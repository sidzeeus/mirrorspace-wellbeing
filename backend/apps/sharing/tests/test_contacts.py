from __future__ import annotations

import re

import pytest
from django.core import mail
from django.db import connection
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.sharing.models import ConsentRecord, SuppressedAddress, TrustedContact
from apps.sharing.services import MAX_CONTACTS, email_fingerprint
from apps.sharing.tokens import INVITE, UNSUBSCRIBE, make_token
from tests.factories import TrustedContactFactory, UserFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

CONTACTS = "/api/v1/trusted-contacts"
VIEW = "/api/v1/contact-invitations/view"
ACCEPT = "/api/v1/contact-invitations/accept"
DECLINE = "/api/v1/contact-invitations/decline"
UNSUB = "/api/v1/unsubscribe"
ONE_CLICK = "/api/v1/unsubscribe/one-click"


@pytest.fixture
def student():
    return UserFactory(display_name="Asha Rao")


@pytest.fixture
def client(student):
    return client_for(student)


def add(client, email="meera@example.test", name="Meera"):
    return client.post(CONTACTS, {"name": name, "email": email}, format="json")


def invite_token() -> str:
    match = re.search(r"/contact-invitation#token=(\S+)", mail.outbox[-1].body)
    assert match, "invitation link not found"
    return match.group(1)


def unsubscribe_token(message=None) -> str:
    match = re.search(r"/unsubscribe#token=(\S+)", (message or mail.outbox[-1]).body)
    assert match, "unsubscribe link not found"
    return match.group(1)


class TestContactIsolation(OwnedResourceContract):
    list_url = CONTACTS
    update_payload = {"name": "changed by intruder"}
    detail_methods = ("get", "patch", "delete")

    def make(self, user):
        return TrustedContactFactory(user=user)


class TestAddContact:
    def test_sends_one_invitation_and_waits(self, client, student):
        response = add(client)

        assert response.status_code == 201
        assert response.json()["status"] == "pending"
        assert len(mail.outbox) == 1
        invitation = mail.outbox[0]
        assert invitation.to == ["meera@example.test"]
        assert "Asha Rao" in invitation.subject
        assert "not monitored" in invitation.body
        assert "/contact-invitation#token=" in invitation.body

    def test_every_email_has_an_unsubscribe_link_and_header(self, client):
        add(client)
        invitation = mail.outbox[0]
        assert "/unsubscribe#token=" in invitation.body
        assert invitation.extra_headers["List-Unsubscribe"].startswith("<http")
        assert invitation.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"

    def test_needs_a_display_name_first(self, user):
        response = add(client_for(user))
        assert response.status_code == 400
        assert response.json()["code"] == "display_name_required"
        assert mail.outbox == []

    def test_rejects_own_address_duplicates_and_bad_input(self, client, student):
        assert add(client, email=student.email.upper()).json()["code"] == "own_email"
        add(client)
        assert add(client, email="MEERA@example.test").json()["code"] == "duplicate_contact"
        assert add(client, email="not-an-email").status_code == 400
        assert add(client, name="   ", email="x@example.test").status_code == 400
        assert len(mail.outbox) == 1

    def test_number_of_contacts_is_limited(self, client):
        for i in range(MAX_CONTACTS):
            assert add(client, email=f"c{i}@example.test").status_code == 201
        response = add(client, email="one.more@example.test")
        assert response.json()["code"] == "too_many_contacts"
        assert len(mail.outbox) == MAX_CONTACTS

    def test_adding_is_rate_limited(self, client):
        statuses = [add(client, email=f"r{i}@example.test").status_code for i in range(11)]
        assert statuses[-1] == 429

    def test_contact_details_are_encrypted_in_the_database(self, client, student):
        add(client, email="meera@example.test", name="Meera Canary")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, email, email_hash FROM sharing_trustedcontact WHERE user_id = %s",
                [student.pk],
            )
            name, email, email_hash = cursor.fetchone()
        assert name.startswith("gAAAA") and email.startswith("gAAAA")
        assert "meera" not in (name + email + email_hash).lower()
        assert len(email_hash) == 64

    def test_address_cannot_be_edited_only_name_and_relationship(self, client, student):
        contact_id = add(client).json()["id"]
        response = client.patch(
            f"{CONTACTS}/{contact_id}",
            {
                "email": "other@example.test",
                "name": "M",
                "relationship": "sister",
                "status": "confirmed",
            },
            format="json",
        )
        contact = TrustedContact.objects.get(pk=contact_id)
        assert response.status_code == 200
        assert (contact.email, contact.name, contact.relationship) == (
            "meera@example.test",
            "M",
            "sister",
        )
        assert contact.status == "pending"

    def test_response_fields(self, client):
        assert set(add(client).json()) == {
            "id",
            "name",
            "email",
            "relationship",
            "status",
            "invited_at",
            "responded_at",
            "created_at",
        }


class TestDoubleOptIn:
    def test_nothing_but_the_invitation_is_sent_before_acceptance(self, client, student):
        contact_id = add(client).json()["id"]
        preview = client.post("/api/v1/sos/preview", {"contact": contact_id}, format="json").json()

        sos = client.post(
            "/api/v1/sos/notify-contact",
            {
                "contact": contact_id,
                "message_hash": preview["message_hash"],
                "idempotency_key": "11111111-1111-4111-8111-111111111111",
                "confirmed": True,
            },
            format="json",
        )
        weekly_preview = client.get(f"/api/v1/sharing/preview?contact={contact_id}").json()
        consent = client.post(
            "/api/v1/sharing/consent",
            {
                "purpose": "weekly_summary",
                "contact": contact_id,
                "notice_version": weekly_preview["notice_version"],
                "preview_hash": weekly_preview["preview_hash"],
                "confirmed": True,
            },
            format="json",
        )

        assert sos.status_code == consent.status_code == 400
        assert sos.json()["code"] == consent.json()["code"] == "contact_not_confirmed"
        assert preview["recipient_can_receive"] is False
        assert len(mail.outbox) == 1  # only the invitation
        assert not ConsentRecord.objects.exists()

    def test_contact_can_see_who_is_asking_before_deciding(self, client, api_client):
        add(client)
        response = api_client.post(VIEW, {"token": invite_token()}, format="json")
        body = response.json()
        assert response.status_code == 200
        assert body["from_name"] == "Asha Rao"
        assert body["status"] == "pending"
        assert "not monitored" in body["limits"]
        # No student data beyond the name they chose to show.
        assert set(body) == {"from_name", "status", "what_you_may_receive", "limits"}

    def test_accepting_confirms_the_contact(self, client, api_client):
        contact_id = add(client).json()["id"]
        response = api_client.post(ACCEPT, {"token": invite_token()}, format="json")
        assert response.status_code == 200
        assert TrustedContact.objects.get(pk=contact_id).status == "confirmed"
        assert client.get(f"{CONTACTS}/{contact_id}").json()["status"] == "confirmed"

    def test_accepting_twice_is_harmless(self, client, api_client):
        add(client)
        token = invite_token()
        api_client.post(ACCEPT, {"token": token}, format="json")
        assert api_client.post(ACCEPT, {"token": token}, format="json").status_code == 200

    def test_declining_closes_the_invitation_for_good(self, client, api_client):
        contact_id = add(client).json()["id"]
        token = invite_token()
        assert api_client.post(DECLINE, {"token": token}, format="json").status_code == 200
        assert TrustedContact.objects.get(pk=contact_id).status == "declined"

        late_accept = api_client.post(ACCEPT, {"token": token}, format="json")
        assert late_accept.status_code == 400
        assert late_accept.json()["code"] == "invitation_closed"
        resend = client.post(f"{CONTACTS}/{contact_id}/resend-invitation")
        assert resend.json()["code"] == "not_pending"

    @pytest.mark.parametrize("token", ["garbage", "a:b:c", ""])
    def test_forged_links_are_rejected(self, api_client, token):
        for url in (VIEW, ACCEPT, DECLINE, UNSUB):
            assert api_client.post(url, {"token": token}, format="json").status_code == 400

    def test_an_unsubscribe_token_cannot_accept_an_invitation(self, api_client, student):
        contact = TrustedContactFactory(user=student, status="pending")
        wrong_purpose = make_token(contact, UNSUBSCRIBE)
        assert api_client.post(ACCEPT, {"token": wrong_purpose}, format="json").status_code == 400
        contact.refresh_from_db()
        assert contact.status == "pending"

    def test_invitation_links_expire(self, api_client, student, settings):
        contact = TrustedContactFactory(user=student, status="pending")
        token = make_token(contact, INVITE)
        settings.CONTACT_INVITATION_MAX_AGE = -1
        assert api_client.post(ACCEPT, {"token": token}, format="json").status_code == 400

    def test_contact_links_need_csrf_like_every_other_form(self, student):
        contact = TrustedContactFactory(user=student, status="pending")
        strict = APIClient(enforce_csrf_checks=True)
        response = strict.post(ACCEPT, {"token": make_token(contact, INVITE)}, format="json")
        assert response.status_code == 403


class TestResendInvitation:
    def test_limited_by_time_and_count(self, client, student):
        contact_id = add(client).json()["id"]
        url = f"{CONTACTS}/{contact_id}/resend-invitation"

        assert client.post(url).json()["code"] == "invitation_too_soon"

        TrustedContact.objects.filter(pk=contact_id).update(invited_at=None)
        assert client.post(url).status_code == 200
        TrustedContact.objects.filter(pk=contact_id).update(invited_at=None)
        assert client.post(url).status_code == 200
        TrustedContact.objects.filter(pk=contact_id).update(invited_at=None)
        assert client.post(url).json()["code"] == "invitation_limit"
        assert len(mail.outbox) == 3


class TestUnsubscribe:
    def test_stops_everything_from_this_student(self, client, api_client, student):
        contact = TrustedContactFactory(user=student, email="meera@example.test")
        consent = ConsentRecord.objects.create(
            user=student,
            contact=contact,
            purpose="weekly_summary",
            notice_version="v",
            granted_at="2026-01-01T00:00:00Z",
            last_confirmed_at="2026-01-01T00:00:00Z",
        )

        response = api_client.post(
            UNSUB, {"token": make_token(contact, UNSUBSCRIBE)}, format="json"
        )

        contact.refresh_from_db()
        consent.refresh_from_db()
        assert response.status_code == 200
        assert contact.status == "unsubscribed"
        assert (consent.status, consent.status_reason) == ("revoked", "contact_unsubscribed")
        assert consent.next_send_at is None
        assert not SuppressedAddress.objects.exists()

    def test_link_from_a_real_email_works(self, client, api_client):
        contact_id = add(client).json()["id"]
        api_client.post(UNSUB, {"token": unsubscribe_token()}, format="json")
        assert TrustedContact.objects.get(pk=contact_id).status == "unsubscribed"

    def test_one_click_header_target_needs_no_cookie_or_csrf(self, student):
        contact = TrustedContactFactory(user=student)
        token = make_token(contact, UNSUBSCRIBE)
        mail_provider = APIClient(enforce_csrf_checks=True)

        response = mail_provider.post(f"{ONE_CLICK}?token={token}")

        contact.refresh_from_db()
        assert response.status_code == 200
        assert contact.status == "unsubscribed"
        assert mail_provider.post(f"{ONE_CLICK}?token=forged").status_code == 400

    def test_block_all_stops_every_student_from_emailing_the_address(self, api_client, student):
        contact = TrustedContactFactory(user=student, email="meera@example.test")
        api_client.post(
            UNSUB, {"token": make_token(contact, UNSUBSCRIBE), "block_all": True}, format="json"
        )
        assert SuppressedAddress.objects.filter(
            email_hash=email_fingerprint("meera@example.test")
        ).exists()

        another = UserFactory(display_name="Someone Else")
        response = add(client_for(another), email="Meera@Example.test")

        assert response.status_code == 201
        assert response.json()["status"] == "unavailable"
        assert mail.outbox == []
        assert not Notification.objects.filter(user=another).exists()

    def test_suppression_list_holds_no_addresses(self, api_client, student):
        contact = TrustedContactFactory(user=student, email="meera@example.test")
        api_client.post(
            UNSUB, {"token": make_token(contact, UNSUBSCRIBE), "block_all": True}, format="json"
        )
        row = SuppressedAddress.objects.values().get()
        assert "meera" not in str(row).lower()

    def test_unsubscribed_contact_gets_no_sos(self, client, api_client, student):
        contact = TrustedContactFactory(user=student)
        api_client.post(UNSUB, {"token": make_token(contact, UNSUBSCRIBE)}, format="json")
        preview = client.post("/api/v1/sos/preview", {"contact": str(contact.pk)}, format="json")
        send = client.post(
            "/api/v1/sos/notify-contact",
            {
                "contact": str(contact.pk),
                "message_hash": preview.json()["message_hash"],
                "idempotency_key": "22222222-2222-4222-8222-222222222222",
                "confirmed": True,
            },
            format="json",
        )
        assert send.status_code == 400
        assert mail.outbox == []


class TestRemoveContact:
    def test_removing_revokes_consent_and_keeps_the_history(self, client, student):
        contact = TrustedContactFactory(user=student)
        consent = ConsentRecord.objects.create(
            user=student,
            contact=contact,
            purpose="weekly_summary",
            notice_version="v",
            granted_at="2026-01-01T00:00:00Z",
            last_confirmed_at="2026-01-01T00:00:00Z",
        )

        assert client.delete(f"{CONTACTS}/{contact.pk}").status_code == 204

        consent.refresh_from_db()
        assert not TrustedContact.objects.filter(pk=contact.pk).exists()
        assert (consent.status, consent.status_reason) == ("revoked", "contact_removed")
        assert consent.contact is None
        history = client.get("/api/v1/sharing/consent").json()["results"]
        assert [row["id"] for row in history] == [str(consent.pk)]
