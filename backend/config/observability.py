"""Logging and error-tracking setup that keeps sensitive text out of both.

Non-negotiable 6: no sensitive text in logs, task names, queue metadata, Sentry or
analytics. Code should log identifiers and event names only. The filters here are the
safety net for when something slips through, not a licence to log content.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

REDACTED = "[redacted]"
REDACTED_EMAIL = "[redacted-email]"

# Extra/log-context keys whose values are never written out, whatever they contain.
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "body",
        "content",
        "cookie",
        "cookies",
        "csrftoken",
        "data",
        "description",
        "display_name",
        "email",
        "label",
        "message",
        "message_body",
        "name",
        "new_password",
        "note",
        "password",
        "phone",
        "prompt",
        "recipient",
        "response",
        "secret",
        "sessionid",
        "text",
        "token",
        "uid",
    }
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(password|new_password|token|secret|authorization|cookie|sessionid|csrftoken)"
    r"(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&)}\]]+)"
)

# Attributes every LogRecord has; anything else was passed through `extra=`.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def redact_text(text: str) -> str:
    """Remove email addresses and credential-looking key/value pairs from free text."""
    text = _EMAIL_RE.sub(REDACTED_EMAIL, text)
    return _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)


def redact_value(key: str, value: Any) -> Any:
    """Redact a structured value, dropping it entirely when the key is sensitive."""
    if key.lower() in SENSITIVE_KEYS:
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(k): redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [redact_value(key, v) for v in value]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return redact_text(str(value))


class RedactionFilter(logging.Filter):
    """Scrub the formatted message and any `extra` fields on every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = None
        for key in list(record.__dict__):
            if key not in _STANDARD_RECORD_ATTRS:
                record.__dict__[key] = redact_value(key, record.__dict__[key])
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, message and extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            # Exception messages can quote user input (for example a database
            # constraint error echoing a value), so they are scrubbed as well.
            payload["exc"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=False)


def scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Strip anything that could carry user content before an event leaves the process."""
    request = event.get("request")
    if isinstance(request, dict):
        url = str(request.get("url", "")).split("?", 1)[0].split("#", 1)[0]
        event["request"] = {"method": request.get("method"), "url": url}

    event.pop("user", None)
    event.pop("extra", None)
    event.pop("breadcrumbs", None)

    if isinstance(event.get("message"), str):
        event["message"] = redact_text(event["message"])
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        if isinstance(logentry.get("message"), str):
            logentry["message"] = redact_text(logentry["message"])
        if isinstance(logentry.get("formatted"), str):
            logentry["formatted"] = redact_text(logentry["formatted"])
        logentry.pop("params", None)

    for container in ("exception", "threads"):
        for item in (event.get(container) or {}).get("values") or []:
            if isinstance(item.get("value"), str):
                item["value"] = redact_text(item["value"])
            for frame in (item.get("stacktrace") or {}).get("frames") or []:
                frame.pop("vars", None)
                frame.pop("pre_context", None)
                frame.pop("post_context", None)
    return event


def drop_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any]) -> None:
    """Breadcrumbs record queries, HTTP calls and log lines. None are needed."""
    return None


def init_sentry(dsn: str, environment: str, release: str | None = None) -> bool:
    """Start Sentry only when a DSN is configured. Returns whether it started."""
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=False,
        include_local_variables=False,
        include_source_context=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        before_send=scrub_sentry_event,  # type: ignore[arg-type]
        before_breadcrumb=drop_breadcrumb,
    )
    return True
