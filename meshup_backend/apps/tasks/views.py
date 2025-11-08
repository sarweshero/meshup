"""Task API views."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.servers.models import Server
from apps.roles.models import ServerMember
from apps.users.models import User

from .models import Task, TaskAttachment, TaskComment
from .serializers import (
    TaskAttachmentSerializer,
    TaskCommentSerializer,
    TaskCreateUpdateSerializer,
    TaskSerializer,
)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tasks within servers."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "priority", "assigned_to", "assigned_by", "channel"]
    search_fields = ["title", "description", "tags"]
    ordering_fields = ["created_at", "due_date", "priority", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return TaskCreateUpdateSerializer
        return TaskSerializer

    def get_queryset(self):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this server's tasks.")
        queryset = (
            Task.objects.filter(server=server, is_deleted=False)
            .select_related("assigned_to", "assigned_by", "server")
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if self.request.query_params.get("assigned_to_me") == "true":
            queryset = queryset.filter(assigned_to=self.request.user)
        return queryset

    def perform_create(self, serializer):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to create tasks for this server.")
        return serializer.save(server=server)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, server_id=None, pk=None):
        task = self.get_object()
        if request.method == "GET":
            comments = task.comments.filter(reply_to__isnull=True)
            serializer = TaskCommentSerializer(comments, many=True, context={"request": request})
            return Response(serializer.data)
        serializer = TaskCommentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def attachments(self, request, server_id=None, pk=None):
        task = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)
        attachment = TaskAttachment.objects.create(
            task=task,
            file=file_obj,
            file_name=file_obj.name,
            file_size=file_obj.size,
            uploaded_by=request.user,
        )
        serializer = TaskAttachmentSerializer(attachment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, server_id=None, pk=None):
        task = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, id=user_id)
        if not ServerMember.objects.filter(
            server=task.server, user=user, is_banned=False
        ).exists():
            return Response({"error": "User is not a member of this server."}, status=status.HTTP_400_BAD_REQUEST)
        task.assigned_to = user
        task.save(update_fields=["assigned_to"])
        serializer = TaskSerializer(task, context={"request": request})
        return Response({"message": "Task assigned successfully", "task": serializer.data})

    @action(detail=True, methods=["post"])
    def complete(self, request, server_id=None, pk=None):
        task = self.get_object()
        task.status = "completed"
        task.progress = 100
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "progress", "completed_at"])
        serializer = TaskSerializer(task, context={"request": request})
        return Response({"message": "Task completed successfully", "task": serializer.data})

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.perform_create(serializer)
        output = TaskSerializer(task, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
