"""Helper for queueing background work safely."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

logger = logging.getLogger(__name__)


def enqueue_on_commit(task: Any, *ids: str) -> None:
    """Queue `task` once the current database transaction has committed.

    Arguments must be identifiers only. Task arguments are stored in the broker and can
    appear in worker logs, so content is always loaded inside the task instead.
    A broker outage is logged and swallowed: every caller has a durable fallback
    (a database flag swept by a periodic task, or a user-visible "send again" action).
    """

    def _send() -> None:
        try:
            task.delay(*ids)
        except Exception:  # noqa: BLE001 - any broker failure must not break the request
            logger.error("task_enqueue_failed", extra={"task": task.name})

    transaction.on_commit(_send)
