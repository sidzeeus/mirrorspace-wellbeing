from django.contrib import admin

from .models import Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    """The helpline directory. Safety plans are never shown in the admin."""

    list_display = ["slug", "name", "region", "type", "status", "verified_on", "owner"]
    list_filter = ["status", "region", "type"]
    search_fields = ["slug", "name"]
    readonly_fields = ["flagged_stale_at"]
