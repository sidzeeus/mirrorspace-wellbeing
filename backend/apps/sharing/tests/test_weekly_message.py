"""The weekly note may carry four fields and nothing else (decision D3)."""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.sharing import weekly
from apps.sharing.notices import WEEKLY_NEUTRAL_LINE
from apps.sharing.weekly import (
    ALLOWED_FIELDS,
    WeeklyFields,
    collect_weekly_fields,
    render_weekly,
)
from tests.factories import (
    CheckInFactory,
    EpisodeFactory,
    ExerciseEventFactory,
    TriggerFactory,
    TrustedContactFactory,
    UserFactory,
)

CANARY = "CANARY-must-never-be-shared"
WEEK_START, WEEK_END = date(2026, 5, 11), date(2026, 5, 17)


def expected_body(name: str, days: int) -> str:
    return (
        f"{name} uses Mirrorspace and chose to send you this short note each week.\n"
        "\n"
        f"Week of 11 May 2026 to 17 May 2026: checked in {days} of 7 days.\n"
        "\n"
        "This is a routine weekly note. Silence does not mean anything either way.\n"
        "\n"
        "Mirrorspace is a self-help tool. It is not monitored by anyone and it is not an "
        "emergency service."
    )


class TestAllowedFields:
    def test_the_list_is_exactly_these_four(self):
        assert ALLOWED_FIELDS == ("display_name", "week_start", "week_end", "check_in_days")

    def test_the_only_input_to_the_renderer_has_exactly_those_fields(self):
        assert tuple(f.name for f in dataclasses.fields(WeeklyFields)) == ALLOWED_FIELDS
        parameters = list(inspect.signature(render_weekly).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].annotation in (WeeklyFields, "WeeklyFields")

    @pytest.mark.django_db
    def test_the_renderer_cannot_reach_the_database(self, django_assert_num_queries):
        fields = WeeklyFields("Asha", WEEK_START, WEEK_END, 3)
        with django_assert_num_queries(0):
            render_weekly(fields)

    def test_template_placeholders_are_all_accounted_for(self):
        import string

        used = {
            name
            for template in (weekly.WEEKLY_SUBJECT, weekly.WEEKLY_BODY)
            for _, name, _, _ in string.Formatter().parse(template)
            if name
        }
        assert used == {*ALLOWED_FIELDS, "neutral_line", "app_name"}

    def test_fixed_line_is_the_agreed_wording(self):
        assert WEEKLY_NEUTRAL_LINE == (
            "This is a routine weekly note. Silence does not mean anything either way."
        )


class TestRenderedNote:
    def test_is_exactly_the_fixed_text_with_the_four_values(self):
        message = render_weekly(WeeklyFields("Asha Rao", WEEK_START, WEEK_END, 3))
        assert message.subject == "Weekly note from Asha Rao"
        assert message.body == expected_body("Asha Rao", 3)

    @pytest.mark.parametrize("days", [0, 1, 7])
    def test_count_wording_never_changes_with_the_number(self, days):
        """No "only", no praise, no concern: the same sentence for 0 and for 7."""
        body = render_weekly(WeeklyFields("Asha", WEEK_START, WEEK_END, days)).body
        assert f"checked in {days} of 7 days." in body
        for judgement in ("only", "great", "well done", "missed", "concern", "worried", "!"):
            assert judgement not in body.lower()

    def test_makes_no_claim_about_how_the_person_is(self):
        body = render_weekly(WeeklyFields("Asha", WEEK_START, WEEK_END, 0)).body.lower()
        for word in ("mood", "sleep", "stress", "energy", "safe", "risk", "okay", "fine", "crisis"):
            assert word not in body


@pytest.mark.django_db
class TestNothingElseLeaks:
    @pytest.fixture
    def loaded_student(self):
        """A student with something private in every table."""
        from apps.safety.models import SafetyPlan

        student = UserFactory(display_name="Asha Rao", email="asha.private@example.test")
        for offset, mood in enumerate((1, 5, 2)):
            CheckInFactory(
                user=student,
                local_date=WEEK_START + timedelta(days=offset),
                mood=mood,
                sleep_hours="3.5",
                sleep_quality=1,
                energy=1,
                stress=5,
            )
        trigger = TriggerFactory(user=student, label=f"{CANARY}-trigger")
        EpisodeFactory(user=student, trigger=trigger, intensity=5, what_helped=f"{CANARY}-helped")
        ExerciseEventFactory(user=student, kind="not_helpful")
        SafetyPlan.objects.create(
            user=student,
            warning_signs=[f"{CANARY}-sign"],
            coping_steps=[f"{CANARY}-step"],
            people=[f"{CANARY}-person"],
        )
        TrustedContactFactory(user=student, name=f"{CANARY}-contact")
        return student

    def test_note_is_identical_to_one_built_from_the_four_fields_alone(self, loaded_student):
        fields = collect_weekly_fields(loaded_student, WEEK_START, WEEK_END)
        message = render_weekly(fields)

        assert fields == WeeklyFields("Asha Rao", WEEK_START, WEEK_END, 3)
        assert message.body == expected_body("Asha Rao", 3)
        assert CANARY not in message.body + message.subject
        assert "asha.private@example.test" not in message.body
        assert "3.5" not in message.body

    def test_collecting_reads_a_count_and_the_name_only(self, loaded_student):
        with CaptureQueriesContext(connection) as queries:
            collect_weekly_fields(loaded_student, WEEK_START, WEEK_END)

        sql = [q["sql"].lower() for q in queries]
        assert len(sql) == 2
        assert any("count(" in statement and "checkins_checkin" in statement for statement in sql)
        joined = " ".join(sql)
        for column in ("mood", "sleep", "energy", "stress", "episodes_", "safety_", "wellbeing_"):
            assert column not in joined, f"the weekly note read '{column}'"

    def test_counts_only_days_inside_the_week(self, loaded_student):
        CheckInFactory(user=loaded_student, local_date=WEEK_START - timedelta(days=1))
        CheckInFactory(user=loaded_student, local_date=WEEK_END + timedelta(days=1))
        assert collect_weekly_fields(loaded_student, WEEK_START, WEEK_END).check_in_days == 3

    def test_counts_only_this_students_check_ins(self, loaded_student):
        other = UserFactory()
        for offset in range(7):
            CheckInFactory(user=other, local_date=WEEK_START + timedelta(days=offset))
        assert collect_weekly_fields(loaded_student, WEEK_START, WEEK_END).check_in_days == 3

    def test_email_that_is_actually_sent_is_the_note_plus_unsubscribe(self, loaded_student):
        from django.core import mail

        from apps.notifications.models import NotificationPurpose
        from apps.notifications.services import create_notification
        from apps.sharing.models import ConsentRecord

        contact = TrustedContactFactory(user=loaded_student, email="meera@example.test")
        now = "2026-05-18T03:30:00Z"
        consent = ConsentRecord.objects.create(
            user=loaded_student,
            contact=contact,
            purpose="weekly_summary",
            notice_version="v",
            granted_at=now,
            last_confirmed_at=now,
        )
        create_notification(
            user=loaded_student,
            purpose=NotificationPurpose.WEEKLY_SUMMARY,
            contact=contact,
            consent=consent,
            idempotency_key="weekly:leak-test",
            context={"week_start": WEEK_START.isoformat(), "week_end": WEEK_END.isoformat()},
        )

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        note, _, footer = sent.body.rpartition("\n\n")
        assert sent.to == ["meera@example.test"]
        assert sent.cc == [] and sent.bcc == []
        assert sent.subject == "Weekly note from Asha Rao"
        assert note == expected_body("Asha Rao", 3)
        assert footer.startswith("To stop receiving these messages: http")
        assert CANARY not in sent.body + sent.subject + str(sent.extra_headers)
