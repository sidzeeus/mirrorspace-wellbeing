from __future__ import annotations

from datetime import date, timedelta

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


class ExerciseFactory(factory.django.DjangoModelFactory):
    """An approved exercise with an approved English translation."""

    class Meta:
        model = "wellbeing.Exercise"
        skip_postgeneration_save = True

    slug = factory.Sequence(lambda n: f"exercise-{n}")
    category = "grounding"
    review_status = "approved"

    @factory.post_generation
    def translations(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return
        from apps.wellbeing.models import ExerciseTranslation

        ExerciseTranslation.objects.create(
            exercise=self,
            language="en",
            title=f"Title of {self.slug}",
            summary="A short summary.",
            steps=["First step.", "Second step."],
            review_status=kwargs.get("review_status", "approved"),
        )


class CheckInFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "checkins.CheckIn"

    user = factory.SubFactory(UserFactory)
    local_date = factory.Sequence(lambda n: date(2026, 1, 1) + timedelta(days=n))
    timezone = "Asia/Kolkata"
    mood = 3


class TriggerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "episodes.Trigger"

    user = factory.SubFactory(UserFactory)
    label = factory.Sequence(lambda n: f"trigger {n}")


class EpisodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "episodes.Episode"

    user = factory.SubFactory(UserFactory)
    occurred_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    intensity = 3


class ExerciseEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "wellbeing.ExerciseEvent"

    user = factory.SubFactory(UserFactory)
    exercise = factory.SubFactory(ExerciseFactory)
    kind = "completed"


class TrustedContactFactory(factory.django.DjangoModelFactory):
    """A contact who has accepted the invitation unless a test says otherwise."""

    class Meta:
        model = "sharing.TrustedContact"

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Contact {n}")
    email = factory.Sequence(lambda n: f"contact{n}@example.test")
    email_hash = factory.LazyAttribute(lambda o: _fingerprint(o.email))
    status = "confirmed"


def _fingerprint(email: str) -> str:
    from apps.sharing.services import email_fingerprint

    return email_fingerprint(email)


class ResourceFactory(factory.django.DjangoModelFactory):
    """A resource a person verified today."""

    class Meta:
        model = "safety.Resource"

    slug = factory.Sequence(lambda n: f"resource-{n}")
    name = factory.Sequence(lambda n: f"Helpline {n}")
    type = "helpline"
    region = "IN"
    languages = ["en"]
    phone = "0000"
    status = "approved"
    owner = "Test Owner"
    verified_on = factory.LazyFunction(lambda: timezone.now().date())
