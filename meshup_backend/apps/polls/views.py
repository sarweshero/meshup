"""Poll API views."""
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.users.serializers import UserBasicSerializer
from apps.roles.models import ServerMember
from apps.servers.models import Server

from .models import Poll, PollComment, PollOption, PollVote
from .serializers import PollCommentSerializer, PollCreateUpdateSerializer, PollSerializer


class PollViewSet(viewsets.ModelViewSet):
    """ViewSet for managing polls and voting."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "created_by", "channel"]
    search_fields = ["question", "description"]
    ordering_fields = ["created_at", "expires_at", "total_votes"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PollCreateUpdateSerializer
        return PollSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Poll.objects.none()

        server_id = self.kwargs.get("server_id")
        if not server_id:
            return Poll.objects.none()

        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this server's polls.")
        return Poll.objects.filter(server=server, is_deleted=False).select_related(
            "created_by", "server"
        ).prefetch_related("options")

    def perform_create(self, serializer):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to create polls for this server.")
        return serializer.save(server=server, created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

    @action(detail=True, methods=["post"])
    def vote(self, request, server_id=None, pk=None):
        poll = self.get_object()
        option_ids = request.data.get("option_ids", [])
        if not option_ids:
            return Response({"error": "option_ids is required"}, status=status.HTTP_400_BAD_REQUEST)
        if poll.status != "active":
            return Response({"error": "Poll is not active"}, status=status.HTTP_400_BAD_REQUEST)
        if poll.is_expired():
            return Response({"error": "Poll has expired"}, status=status.HTTP_400_BAD_REQUEST)
        unique_option_ids = list({str(option_id) for option_id in option_ids})
        if not poll.allow_multiple_votes and len(unique_option_ids) > 1:
            return Response({"error": "This poll only allows one vote"}, status=status.HTTP_400_BAD_REQUEST)
        existing_votes = PollVote.objects.filter(poll=poll, user=request.user)
        if not poll.allow_multiple_votes and existing_votes.exists():
            return Response({"error": "You have already voted on this poll"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            if poll.allow_multiple_votes and existing_votes.exists():
                option_ids_to_decrement = existing_votes.values_list("option_id", flat=True)
                PollOption.objects.filter(id__in=option_ids_to_decrement).update(
                    vote_count=F("vote_count") - 1
                )
                existing_votes.delete()
            for option_id in unique_option_ids:
                option = get_object_or_404(PollOption, id=option_id, poll=poll)
                PollVote.objects.create(poll=poll, option=option, user=request.user)
                PollOption.objects.filter(id=option.id).update(vote_count=F("vote_count") + 1)
            poll.total_votes = poll.votes.values("user").distinct().count()
            poll.save(update_fields=["total_votes"])
        serializer = PollSerializer(poll, context={"request": request})
        return Response({"message": "Vote recorded successfully", "poll": serializer.data})

    @action(detail=True, methods=["delete"])
    def unvote(self, request, server_id=None, pk=None):
        poll = self.get_object()
        with transaction.atomic():
            votes = PollVote.objects.filter(poll=poll, user=request.user)
            if not votes.exists():
                return Response({"error": "You have not voted on this poll"}, status=status.HTTP_400_BAD_REQUEST)
            option_ids = votes.values_list("option_id", flat=True)
            PollOption.objects.filter(id__in=option_ids).update(vote_count=F("vote_count") - 1)
            votes.delete()
            poll.total_votes = poll.votes.values("user").distinct().count()
            poll.save(update_fields=["total_votes"])
        return Response({"message": "Vote removed successfully"})

    @action(detail=True, methods=["get"])
    def results(self, request, server_id=None, pk=None):
        poll = self.get_object()
        if not poll.show_results_before_vote:
            user_voted = poll.votes.filter(user=request.user).exists()
            if not user_voted and poll.status == "active":
                return Response(
                    {"error": "You must vote before viewing results"}, status=status.HTTP_403_FORBIDDEN
                )
        options_data = []
        for option in poll.options.all():
            option_result = {
                "id": str(option.id),
                "option_text": option.option_text,
                "vote_count": option.vote_count,
                "percentage": round(option.calculate_percentage(), 2),
            }
            if not poll.anonymous_votes:
                voters = [vote.user for vote in option.votes.all()]
                option_result["voters"] = UserBasicSerializer(voters, many=True).data
            options_data.append(option_result)
        return Response({"question": poll.question, "total_votes": poll.total_votes, "options": options_data})

    @action(detail=True, methods=["post"])
    def close(self, request, server_id=None, pk=None):
        poll = self.get_object()
        if (
            poll.created_by != request.user
            and poll.server.owner != request.user
            and not request.user.is_admin
        ):
            return Response(
                {"error": "Only poll creator or admin can close the poll"},
                status=status.HTTP_403_FORBIDDEN,
            )
        poll.status = "closed"
        poll.closed_at = timezone.now()
        poll.save(update_fields=["status", "closed_at"])
        return Response({"message": "Poll closed successfully"})

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, server_id=None, pk=None):
        poll = self.get_object()
        if request.method == "GET":
            comments = poll.comments.all()
            serializer = PollCommentSerializer(comments, many=True, context={"request": request})
            return Response(serializer.data)
        serializer = PollCommentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(poll=poll, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = self.perform_create(serializer)
        output = PollSerializer(poll, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
