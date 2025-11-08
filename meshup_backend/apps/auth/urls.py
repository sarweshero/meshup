"""Authentication URL patterns for Meshup platform."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserRegistrationView,
)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
