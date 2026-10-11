from __future__ import annotations

import factory
from django.utils import timezone

from apps.accounts.models import User

DEFAULT_PASSWORD = "correct-horse-battery-staple"


class UserFactory(factory.django.DjangoModelFactory):
    """A verified, active, 18+ confirmed user unless a test says otherwise."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"student{n}@example.test")
    email_verified_at = factory.LazyFunction(timezone.now)
    age_confirmed_at = factory.LazyFunction(timezone.now)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.setdefault("password", DEFAULT_PASSWORD)
        return model_class.objects.create_user(*args, **kwargs)
