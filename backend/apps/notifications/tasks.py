"""Notification tasks. Arguments are ids only; names say nothing about content."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="notifications.deliver")
def deliver(notification_id: str) -> None:
    from . import services
    from .models import Notification

    outcome = services.attempt(notification_id)
    if outcome is services.Outcome.RETRY:
        retry_count = (
            Notification.objects.filter(pk=notification_id)
            .values_list("retry_count", flat=True)
            .first()
            or 1
        )
        deliver.apply_async((notification_id,), countdown=services.retry_delay(retry_count))


@shared_task(name="notifications.enqueue_due_weekly")
def enqueue_due_weekly() -> None:
    from . import services

    services.enqueue_due_weekly()


@shared_task(name="notifications.sweep_stuck")
def sweep_stuck() -> None:
    from . import services

    services.sweep_stuck()
