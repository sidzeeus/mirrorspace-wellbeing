"""Field-level encryption for the free text students write.

Values are encrypted with Fernet (AES-128-CBC + HMAC) before they reach PostgreSQL, so
a database dump, backup or read-only database account does not expose them. Keys come
from FIELD_ENCRYPTION_KEYS: the first key encrypts, every key can decrypt, which is how
a key is rotated without downtime.

Because each encryption uses a fresh random IV, the same text never produces the same
stored value. That is deliberate, and it means these columns cannot be searched,
sorted or made unique in SQL.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


@lru_cache(maxsize=4)
def _cipher(keys: tuple[str, ...]) -> MultiFernet:
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS must contain at least one Fernet key.")
    return MultiFernet([Fernet(key.encode()) for key in keys])


def encrypt(text: str) -> str:
    return _cipher(tuple(settings.FIELD_ENCRYPTION_KEYS)).encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _cipher(tuple(settings.FIELD_ENCRYPTION_KEYS)).decrypt(token.encode()).decode()


class EncryptedTextField(models.TextField):
    """A text column that is encrypted at rest. Empty strings are stored as empty."""

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> str | None:
        if value is None or value == "":
            return value
        return decrypt(value)

    def get_prep_value(self, value: Any) -> str | None:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))
