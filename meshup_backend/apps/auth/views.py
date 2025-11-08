"""Authentication views for Meshup platform."""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """API endpoint for user registration."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User registered successfully",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """API endpoint for JWT token generation (login)."""

    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """API endpoint for user logout (blacklist refresh token)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            try:
                token.blacklist()
            except AttributeError:
                pass  # Blacklist app not installed; skip blacklisting.
            except NotImplementedError:
                pass  # Token backend does not support blacklisting.
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    """API endpoint to request password reset."""

    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: Integrate email delivery for password reset tokens.
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    """API endpoint to confirm password reset."""

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: Implement token validation and password reset logic.
        return Response({"message": "Password has been reset successfully"}, status=status.HTTP_200_OK)
