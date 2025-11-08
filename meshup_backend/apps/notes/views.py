"""Views for collaborative notes."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.servers.models import Server
from apps.roles.models import ServerMember

from .models import Note, NoteVersion
from .serializers import (
    NoteCreateUpdateSerializer,
    NoteSerializer,
    NoteVersionSerializer,
)


class NoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing server notes."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_pinned", "is_locked", "created_by"]
    search_fields = ["title", "content", "tags"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-is_pinned", "-updated_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return NoteCreateUpdateSerializer
        return NoteSerializer

    def get_queryset(self):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this server's notes.")
        return Note.objects.filter(server=server, is_deleted=False).select_related(
            "created_by", "last_edited_by"
        )

    def perform_create(self, serializer):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to create notes in this server.")
        note = serializer.save(server=server, created_by=self.request.user, last_edited_by=self.request.user)
        NoteVersion.objects.create(
            note=note,
            version_number=1,
            title=note.title,
            content=note.content,
            edited_by=self.request.user,
            change_description="Initial version",
        )
        return note

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

    @action(detail=True, methods=["get"])
    def versions(self, request, server_id=None, pk=None):
        note = self.get_object()
        versions = note.version_history.all()
        serializer = NoteVersionSerializer(versions, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, server_id=None, pk=None):
        note = self.get_object()
        version_number = request.data.get("version_number")
        if not version_number:
            return Response({"error": "version_number is required"}, status=status.HTTP_400_BAD_REQUEST)
        version = get_object_or_404(NoteVersion, note=note, version_number=version_number)
        NoteVersion.objects.create(
            note=note,
            version_number=note.version,
            title=note.title,
            content=note.content,
            edited_by=request.user,
            change_description=f"Before restore to v{version_number}",
        )
        note.title = version.title
        note.content = version.content
        note.last_edited_by = request.user
        note.save(update_fields=["title", "content", "last_edited_by"])
        NoteVersion.objects.create(
            note=note,
            version_number=note.version,
            title=note.title,
            content=note.content,
            edited_by=request.user,
            change_description=f"Restored to version {version_number}",
        )
        serializer = NoteSerializer(note, context={"request": request})
        return Response({"message": f"Note restored to version {version_number}", "note": serializer.data})

    @action(detail=True, methods=["post"])
    def pin(self, request, server_id=None, pk=None):
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=["is_pinned"])
        status_text = "pinned" if note.is_pinned else "unpinned"
        return Response({"message": f"Note {status_text} successfully", "is_pinned": note.is_pinned})

    @action(detail=True, methods=["post"])
    def lock(self, request, server_id=None, pk=None):
        note = self.get_object()
        note.is_locked = not note.is_locked
        note.save(update_fields=["is_locked"])
        status_text = "locked" if note.is_locked else "unlocked"
        return Response({"message": f"Note {status_text} successfully", "is_locked": note.is_locked})

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = self.perform_create(serializer)
        output = NoteSerializer(note, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
