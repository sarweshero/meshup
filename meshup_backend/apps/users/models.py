"""User models for Meshup platform."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, username, password=None, **extra_fields):
        """Create and return a regular user with email and password."""
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and return a superuser with admin privileges."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with extended fields for Meshup platform."""

    STATUS_CHOICES = (
        ("online", "Online"),
        ("away", "Away"),
        ("dnd", "Do Not Disturb"),
        ("offline", "Offline"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=50, unique=True, db_index=True)
    discriminator = models.CharField(max_length=4, default="0001")

    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="offline")
    custom_status = models.CharField(max_length=100, blank=True)

    is_bot = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.username}#{self.discriminator}"

    def get_full_identifier(self) -> str:
        """Return username with discriminator."""
        return f"{self.username}#{self.discriminator}"
