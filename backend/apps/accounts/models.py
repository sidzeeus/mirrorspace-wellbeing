from __future__ import annotations

import uuid
import zoneinfo
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email(email: str) -> str:
    """Addresses are compared and stored in lower case so one person has one account."""
    return email.strip().lower()


def validate_timezone(value: str) -> None:
    if value not in zoneinfo.available_timezones():
        raise ValidationError("Choose a valid time zone, for example Asia/Kolkata.")


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        if not email:
            raise ValueError("An email address is required.")
        timezone_name = extra.pop("timezone", settings.DEFAULT_USER_TIMEZONE)
        display_name = extra.pop("display_name", "")
        user = self.model(email=normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        Profile.objects.using(self._db).create(
            user=user, timezone=timezone_name, display_name=display_name
        )
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verified_at", timezone.now())
        extra.setdefault("age_confirmed_at", timezone.now())
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, username: str | None) -> User:
        return self.get(email=normalize_email(username or ""))


class User(AbstractBaseUser, PermissionsMixin):
    """A student account. Email is the login; there is no username."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    preferred_language = models.CharField(
        max_length=8, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # The person stated they are 18 or older. Registration is refused without it.
    age_confirmed_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Set when the person asks for deletion. The account is locked at once and a
    # background task removes it; a periodic sweep catches any task that was lost.
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]
        indexes = [
            models.Index(fields=["deletion_requested_at"], name="accounts_user_deletion_idx"),
        ]

    def __str__(self) -> str:
        # Never the email address: this string ends up in logs and admin history.
        return f"user:{self.pk}"

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class Profile(models.Model):
    """Optional presentation details. Kept apart from credentials on purpose."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=60, blank=True)
    # Used only to work out the person's local date and to schedule their email.
    timezone = models.CharField(
        max_length=64, default="Asia/Kolkata", validators=[validate_timezone]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"profile:{self.user_id}"
