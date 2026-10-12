from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"
    label = "chat"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import ChatFeedback, ChatMessage, ChatSession, ChatUsage

        register_export(
            "chat",
            (ChatSession, ChatMessage, ChatFeedback, ChatUsage),
            lambda user: {
                "sessions": [
                    {
                        "id": str(session.pk),
                        "created_at": session.created_at.isoformat(),
                        "save_transcript": session.save_transcript,
                        "retention_days": session.retention_days,
                        "expires_at": session.expires_at.isoformat()
                        if session.expires_at
                        else None,
                        "messages": [
                            {
                                "role": message.role,
                                "kind": message.kind,
                                "content": message.content,
                                "created_at": message.created_at.isoformat(),
                            }
                            for message in session.messages.all()
                        ],
                    }
                    for session in ChatSession.objects.filter(user=user).prefetch_related(
                        "messages"
                    )
                ],
                "feedback": [
                    {
                        "kind": item.kind,
                        "helpful": item.helpful,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in ChatFeedback.objects.filter(user=user)
                ],
                "usage": [
                    {"day": item.day.isoformat(), "replies": item.replies}
                    for item in ChatUsage.objects.filter(user=user).order_by("day")
                ],
            },
        )
