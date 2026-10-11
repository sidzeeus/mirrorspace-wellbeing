from django.contrib import admin
from django.http import HttpRequest

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Operators can see that an account exists and lock it. Nothing more.

    Profiles and all wellbeing data are deliberately not registered in the admin.
    """

    list_display = ["id", "is_active", "is_staff", "email_verified_at", "created_at"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["=email"]
    ordering = ["-created_at"]
    fields = [
        "id",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified_at",
        "age_confirmed_at",
        "deletion_requested_at",
        "created_at",
        "last_login",
    ]
    readonly_fields = [
        "id",
        "email",
        "email_verified_at",
        "age_confirmed_at",
        "deletion_requested_at",
        "created_at",
        "last_login",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
