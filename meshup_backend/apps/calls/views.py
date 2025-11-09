"""Views for voice and video call management."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CallInvitation,
    CallParticipant,
    CallQualityMetric,
    CallRecording,
    CallSession,
    ScreenShareSession,
)
from .serializers import (
    CallInvitationSerializer,
    CallParticipantSerializer,
    CallQualityMetricSerializer,
    CallRecordingSerializer,
    CallSessionDetailSerializer,
    CallSessionListSerializer,
    ScreenShareSessionSerializer,
    InitiateCallSerializer,
    ScreenShareStartSerializer,
    UpdateMediaStateSerializer,
)
from apps.servers.models import Server

logger = logging.getLogger(__name__)


class CallSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing voice and video call sessions."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["call_type", "status", "initiator", "server"]
    ordering_fields = ["created_at", "started_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return CallSessionListSerializer
        if self.action == "retrieve":
            return CallSessionDetailSerializer
        return CallSessionDetailSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            CallSession.objects.filter(server__members__user=user)
            .select_related("initiator", "channel", "dm_channel", "server")
            .prefetch_related("participants__user", "screen_shares", "recording")
            .distinct()
        )

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        limit_days = int(request.query_params.get("limit_days", 30))
        cutoff_date = timezone.now() - timedelta(days=limit_days)

        queryset = self.get_queryset().filter(created_at__gte=cutoff_date)
        filtered_qs = self.filter_queryset(queryset)
        page = self.paginate_queryset(filtered_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(filtered_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def initiate(self, request):
        serializer = InitiateCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        call_type = serializer.validated_data["call_type"]
        recipients = serializer.validated_data["recipients"]
        channel_id = serializer.validated_data.get("channel_id")
        dm_channel_id = serializer.validated_data.get("dm_channel_id")
        video_quality = serializer.validated_data.get("video_quality", "standard")
        enable_recording = serializer.validated_data.get("enable_recording", False)

        from apps.users.models import User

        recipients_list = []
        for recipient_id in recipients:
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:  # pragma: no cover - defensive branch
                return Response({"error": f"User {recipient_id} not found"}, status=status.HTTP_400_BAD_REQUEST)
            recipients_list.append(recipient)

        channel = None
        dm_channel = None
        server: Server | None = None

        if channel_id:
            from apps.channels.models import Channel

            channel = get_object_or_404(Channel, id=channel_id)
            server = channel.server
        elif dm_channel_id:
            from apps.messages.models import DirectMessage

            dm_channel = get_object_or_404(DirectMessage, id=dm_channel_id)
            if recipients_list:
                membership = recipients_list[0].server_memberships.first()
                server = membership.server if membership else None

        if not server:
            return Response({"error": "Could not determine server context"}, status=status.HTTP_400_BAD_REQUEST)

        call_id = uuid.uuid4()
        room_id = f"room_{call_id}"
        call_token = self.generate_call_token(call_id)

        try:
            with transaction.atomic():
                call = CallSession.objects.create(
                    call_type=call_type,
                    initiator=request.user,
                    status="ringing" if recipients_list else "initiating",
                    channel=channel,
                    dm_channel=dm_channel,
                    server=server,
                    room_id=room_id,
                    call_token=call_token,
                    video_quality=video_quality,
                    total_participants=len(recipients_list) + 1,
                )

                initiator_peer_id = f"peer_{uuid.uuid4()}"
                CallParticipant.objects.create(
                    call=call,
                    user=request.user,
                    peer_id=initiator_peer_id,
                )

                for recipient in recipients_list:
                    CallInvitation.objects.create(
                        call=call,
                        recipient=recipient,
                        status="pending",
                        notification_sent=True,
                        notification_type="inapp",
                    )

                if enable_recording:
                    call.is_recorded = True
                    call.save(update_fields=["is_recorded"])
        except Exception as exc:  # pragma: no cover - transactional safety
            logger.exception("Error initiating call: %s", exc)
            return Response({"error": "Failed to initiate call"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.broadcast_call_invitation(call, recipients_list)
        response_serializer = CallSessionDetailSerializer(call)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        call = self.get_object()

        if call.status in {"ended", "declined", "missed"}:
            return Response({"error": "Call is no longer active"}, status=status.HTTP_400_BAD_REQUEST)

        if call.initiator != request.user:
            invitation = CallInvitation.objects.filter(call=call, recipient=request.user).first()
            if not invitation:
                return Response({"error": "Not invited to this call"}, status=status.HTTP_403_FORBIDDEN)
            invitation.status = "accepted"
            invitation.responded_at = timezone.now()
            invitation.response_time_seconds = int((timezone.now() - call.created_at).total_seconds())
            invitation.save()

        participant = CallParticipant.objects.filter(call=call, user=request.user).first()

        peer_id = f"peer_{uuid.uuid4()}"

        if participant and participant.left_at is None:
            # Participant was pre-created or is already active; just confirm state.
            if call.status == "ringing":
                call.status = "active"
                call.started_at = timezone.now()
                call.save(update_fields=["status", "started_at"])
            serializer = CallParticipantSerializer(participant)
            return Response({"message": "Already in call", "participant": serializer.data})

        if participant and participant.left_at is not None:
            # Reactivate participant who previously left.
            participant.left_at = None
            participant.joined_at = timezone.now()
            participant.peer_id = peer_id
            participant.save(update_fields=["left_at", "joined_at", "peer_id"])
        else:
            participant = CallParticipant.objects.create(call=call, user=request.user, peer_id=peer_id)

        if call.status == "ringing":
            call.status = "active"
            call.started_at = timezone.now()
            call.save(update_fields=["status", "started_at"])

        active_count = call.get_active_participants_count()
        if active_count > call.peak_participants:
            call.peak_participants = active_count
            call.save(update_fields=["peak_participants"])

        total_participants = call.participants.count()
        fields_to_update: list[str] = []
        if total_participants > call.total_participants:
            call.total_participants = total_participants
            fields_to_update.append("total_participants")
        if fields_to_update:
            call.save(update_fields=fields_to_update)

        self.broadcast_participant_joined(call, participant)
        serializer = CallParticipantSerializer(participant)
        return Response({"message": "Joined call successfully", "participant": serializer.data})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        call = self.get_object()
        participant = CallParticipant.objects.filter(call=call, user=request.user, left_at__isnull=True).first()
        if not participant:
            return Response({"error": "Not currently in call"}, status=status.HTTP_400_BAD_REQUEST)

        participant.left_at = timezone.now()
        participant.save(update_fields=["left_at"])
        duration = participant.get_duration()

        if call.get_active_participants_count() == 0:
            call.status = "ended"
            call.ended_at = timezone.now()
            call.save(update_fields=["status", "ended_at"])

        self.broadcast_participant_left(call, participant)
        return Response({"message": "Left call successfully", "duration_seconds": duration})

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        call = self.get_object()
        if call.initiator != request.user:
            return Response({"error": "Only initiator can end call"}, status=status.HTTP_403_FORBIDDEN)
        if call.status == "ended":
            return Response({"error": "Call already ended"}, status=status.HTTP_400_BAD_REQUEST)

        CallParticipant.objects.filter(call=call, left_at__isnull=True).update(left_at=timezone.now())
        call.status = "ended"
        call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])

        self.broadcast_call_ended(call)
        return Response(
            {
                "message": "Call ended",
                "duration_seconds": call.get_duration(),
                "participant_count": call.participants.count(),
            }
        )

    @action(detail=True, methods=["post"])
    def update_media(self, request, pk=None):
        call = self.get_object()
        serializer = UpdateMediaStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participant = CallParticipant.objects.filter(call=call, user=request.user, left_at__isnull=True).first()
        if not participant:
            return Response({"error": "Not in call"}, status=status.HTTP_400_BAD_REQUEST)

        if "audio_state" in serializer.validated_data:
            participant.audio_state = serializer.validated_data["audio_state"]
        if "video_state" in serializer.validated_data:
            participant.video_state = serializer.validated_data["video_state"]
        if "screen_share_state" in serializer.validated_data:
            participant.screen_share_state = serializer.validated_data["screen_share_state"]
        participant.save()

        self.broadcast_media_state_changed(call, participant)
        participant_serializer = CallParticipantSerializer(participant)
        return Response({"participant": participant_serializer.data})

    @action(detail=True, methods=["post"], url_path="screen-share/start")
    def screen_share_start(self, request, pk=None):
        call = self.get_object()
        serializer = ScreenShareStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participant = CallParticipant.objects.filter(call=call, user=request.user, left_at__isnull=True).first()
        if not participant:
            return Response({"error": "Not in call"}, status=status.HTTP_400_BAD_REQUEST)

        existing = ScreenShareSession.objects.filter(participant=participant, status__in=["active", "paused"]).first()
        if existing:
            return Response({"error": "Already sharing screen"}, status=status.HTTP_400_BAD_REQUEST)

        stream_id = f"stream_{uuid.uuid4()}"
        screen_share = ScreenShareSession.objects.create(
            call=call,
            participant=participant,
            stream_id=stream_id,
            resolution=serializer.validated_data.get("resolution", "1920x1080"),
            framerate=serializer.validated_data.get("framerate", 30),
            bitrate_kbps=serializer.validated_data.get("bitrate_kbps", 2500),
            include_audio=serializer.validated_data.get("include_audio", False),
        )

        participant.screen_share_state = "active"
        participant.save(update_fields=["screen_share_state"])

        self.broadcast_screen_share_started(call, screen_share)
        response_serializer = ScreenShareSessionSerializer(screen_share)
        return Response({"screen_share": response_serializer.data, "stream_id": stream_id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="screen-share/end")
    def screen_share_end(self, request, pk=None):
        call = self.get_object()
        participant = CallParticipant.objects.filter(call=call, user=request.user, left_at__isnull=True).first()
        if not participant:
            return Response({"error": "Not in call"}, status=status.HTTP_400_BAD_REQUEST)

        screen_share = ScreenShareSession.objects.filter(participant=participant, status__in=["active", "paused"]).first()
        if not screen_share:
            return Response({"error": "No active screen share"}, status=status.HTTP_400_BAD_REQUEST)

        screen_share.status = "ended"
        screen_share.ended_at = timezone.now()
        screen_share.save(update_fields=["status", "ended_at"])

        participant.screen_share_state = "inactive"
        participant.save(update_fields=["screen_share_state"])

        self.broadcast_screen_share_ended(call, screen_share)
        return Response({"message": "Screen share ended"})

    @action(detail=True, methods=["get"])
    def participants(self, request, pk=None):
        call = self.get_object()
        participants = call.participants.select_related("user").all()
        serializer = CallParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="quality-metrics")
    def quality_metrics(self, request, pk=None):
        call = self.get_object()
        participant_id = request.query_params.get("participant_id")
        limit = int(request.query_params.get("limit", 100))

        metrics = CallQualityMetric.objects.filter(call=call)
        if participant_id:
            metrics = metrics.filter(participant_id=participant_id)
        metrics = metrics.order_by("-recorded_at")[:limit]

        serializer = CallQualityMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="recording")
    def recording(self, request, pk=None):
        call = self.get_object()

        if request.method == "GET":
            recording = getattr(call, "recording", None)
            if not recording:
                return Response({"error": "No recording for this call"}, status=status.HTTP_404_NOT_FOUND)
            serializer = CallRecordingSerializer(recording)
            return Response(serializer.data)

        action_name = request.data.get("action")
        if action_name == "start":
            if getattr(call, "recording", None):
                return Response({"error": "Recording already exists"}, status=status.HTTP_400_BAD_REQUEST)
            recording = CallRecording.objects.create(
                call=call,
                status="recording",
                file_url="",
                file_size=0,
                duration_seconds=0,
            )
            self.broadcast_recording_started(call)
            serializer = CallRecordingSerializer(recording)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if action_name == "stop":
            recording = getattr(call, "recording", None)
            if not recording:
                return Response({"error": "No active recording"}, status=status.HTTP_400_BAD_REQUEST)
            recording.status = "processing"
            recording.completed_at = timezone.now()
            recording.save(update_fields=["status", "completed_at"])
            # Placeholder for async processing integration
            return Response({"message": "Recording stopped, processing started"})

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    # Helper methods -------------------------------------------------

    def generate_call_token(self, call_id: uuid.UUID) -> str:
        return secrets.token_urlsafe(64)

    def broadcast_call_invitation(self, call: CallSession, recipients: list):  # pragma: no cover - I/O heavy
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        for recipient in recipients:
            async_to_sync(channel_layer.group_send)(
                f"presence_{call.server.id}",
                {
                    "type": "call_invitation",
                    "call_id": str(call.id),
                    "call_type": call.call_type,
                    "initiator": call.initiator.username,
                    "recipient_id": str(recipient.id),
                },
            )

    def broadcast_participant_joined(self, call: CallSession, participant: CallParticipant) -> None:
        payload = {
            "type": "call_participant_joined",
            "call_id": str(call.id),
            "participant": CallParticipantSerializer(participant).data,
        }
        self._send_call_event(call, payload)

    def broadcast_participant_left(self, call: CallSession, participant: CallParticipant) -> None:
        payload = {
            "type": "call_participant_left",
            "call_id": str(call.id),
            "participant": CallParticipantSerializer(participant).data,
        }
        self._send_call_event(call, payload)

    def broadcast_call_ended(self, call: CallSession) -> None:
        payload = {
            "type": "call_ended",
            "call_id": str(call.id),
            "status": call.status,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": call.get_duration(),
        }
        self._send_call_event(call, payload)

    def broadcast_media_state_changed(self, call: CallSession, participant: CallParticipant) -> None:
        payload = {
            "type": "call_media_state",
            "call_id": str(call.id),
            "participant": CallParticipantSerializer(participant).data,
        }
        self._send_call_event(call, payload)

    def broadcast_screen_share_started(self, call: CallSession, screen_share: ScreenShareSession) -> None:
        payload = {
            "type": "call_screen_share_started",
            "call_id": str(call.id),
            "screen_share": ScreenShareSessionSerializer(screen_share).data,
        }
        self._send_call_event(call, payload)

    def broadcast_screen_share_ended(self, call: CallSession, screen_share: ScreenShareSession) -> None:
        payload = {
            "type": "call_screen_share_ended",
            "call_id": str(call.id),
            "screen_share": ScreenShareSessionSerializer(screen_share).data,
        }
        self._send_call_event(call, payload)

    def broadcast_recording_started(self, call: CallSession) -> None:
        recording = getattr(call, "recording", None)
        payload = {
            "type": "call_recording_started",
            "call_id": str(call.id),
            "recording": CallRecordingSerializer(recording).data if recording else None,
        }
        self._send_call_event(call, payload)

    def _send_call_event(self, call: CallSession, payload: dict[str, object]) -> None:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(f"call_{call.id}", payload)
