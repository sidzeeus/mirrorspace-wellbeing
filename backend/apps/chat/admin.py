from django.contrib import admin

from .models import ContentDocument


@admin.register(ContentDocument)
class ContentDocumentAdmin(admin.ModelAdmin):
    """Reviewed knowledge for the chat. Conversations are never shown in the admin.

    After approving or editing a document, run `python manage.py index_knowledge`.
    """

    list_display = ["slug", "title", "language", "review_status", "reviewed_on", "version"]
    list_filter = ["review_status", "language"]
    search_fields = ["slug", "title"]
