from django.contrib import admin

from .models import Exercise, ExerciseTranslation


class ExerciseTranslationInline(admin.StackedInline):
    model = ExerciseTranslation
    extra = 0


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    """Content editors manage exercises here. Student feedback is not shown."""

    list_display = ["slug", "category", "review_status", "version", "reviewed_on"]
    list_filter = ["category", "review_status"]
    search_fields = ["slug"]
    inlines = [ExerciseTranslationInline]
