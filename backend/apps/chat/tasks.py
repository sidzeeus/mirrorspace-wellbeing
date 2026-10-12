from __future__ import annotations

from celery import shared_task


@shared_task(name="chat.purge_expired")
def purge_expired() -> None:
    from . import services

    services.purge_expired()
