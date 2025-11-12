from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AbstractUser, PermissionsMixin, Group, Permission
from django.db import models
from django.utils import timezone
import secrets
from django.conf import settings
from common.validators import *
from .managers import CustomUserManager
from .utils.email_verification import generate_verification_token
from common.models import BaseModel


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = None
    email = models.EmailField(unique=True, validators=[validate_email_format])
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(
        max_length=20, blank=True, validators=[validate_phone_number]
    )

    # Email verification
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    verification_token_expires = models.DateTimeField(blank=True, null=True)

    # Security fields
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    google_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="coreuser_groups",
        related_query_name="coreuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="coreuser_permissions",
        related_query_name="coreuser",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def is_verification_code_valid(self, code):
        """Check if verification code is valid and not expired"""
        return (
            self.verification_token
            and secrets.compare_digest(self.verification_token, code)
            and timezone.now() < self.verification_token_expires
        )

    def verify_email(self):
        """Mark user's email as verified and clear token info"""
        self.email_verified = True
        self.verification_token = None
        self.verification_token_expires = None
        self.save(
            update_fields=[
                "email_verified",
                "verification_token",
                "verification_token_expires",
            ]
        )


class PasswordResetToken(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    @classmethod
    def create_token(cls, user):
        """Create a new password reset token"""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        # Invalidate existing tokens
        cls.objects.filter(user=user, used=False).update(used=True)

        return cls.objects.create(user=user, token=token, expires_at=expires_at)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Mark token as used"""
        self.used = True
        self.save(update_fields=["used"])


class EmailVerificationAttempt(BaseModel):
    email = models.EmailField()
    token = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)

    class Meta:
        db_table = "email_verification_attempts"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["email", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        return f"Verification attempt for {self.email} at {self.timestamp}"
