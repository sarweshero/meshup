"""User API views for Meshup platform."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .serializers import UserBasicSerializer, UserDetailSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Manage user profiles and preferences."""

    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["username", "email"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and not self.request.user.is_admin:
            queryset = queryset.filter(id=self.request.user.id)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(username__icontains=search) | Q(email__icontains=search))
        return queryset

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserDetailSerializer
        if self.action in {"me", "me_update"}:
            return UserDetailSerializer
        return UserDetailSerializer

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        instance = self.get_object()
        if instance != request.user and not request.user.is_admin:
            raise PermissionDenied("You do not have permission to update this user.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        instance = self.get_object()
        if instance != request.user and not request.user.is_admin:
            raise PermissionDenied("You do not have permission to update this user.")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        return Response({"detail": "Deletion via API is disabled."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        instance = self.get_object()
        if instance != request.user and not request.user.is_admin:
            raise PermissionDenied("You do not have permission to view this user.")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Return the authenticated user's profile."""
        serializer = UserDetailSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    @me.mapping.patch
    def me_update(self, request):
        """Partially update the authenticated user's profile."""
        serializer = UserDetailSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
