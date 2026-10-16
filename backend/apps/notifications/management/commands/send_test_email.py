"""Check that email delivery works: send one plain test email.

    python manage.py send_test_email you@example.com

Uses the same settings as every other email (EMAIL_BACKEND, EMAIL_HOST ...). Prints
whether the mail server accepted the message, and on failure only the kind of error,
never the server's reply, which can quote the address.
"""

from __future__ import annotations

import smtplib
from typing import Any

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError, CommandParser

BODY = (
    "This is a test email from {app_name}.\n\n"
    "If you can read this, email delivery is working. You do not need to do anything."
)


class Command(BaseCommand):
    help = "Send one test email to check the email settings."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("address", help="Where to send the test email.")

    def handle(self, *args: Any, **options: Any) -> None:
        message = EmailMessage(
            subject=f"{settings.APP_NAME}: test email",
            body=BODY.format(app_name=settings.APP_NAME),
            to=[options["address"]],
        )
        try:
            message.send(fail_silently=False)
        except smtplib.SMTPAuthenticationError:
            raise CommandError(
                "The mail server refused the username or password (EMAIL_HOST_USER, "
                "EMAIL_HOST_PASSWORD). For Gmail, use an app password."
            ) from None
        except smtplib.SMTPResponseException as exc:
            raise CommandError(
                f"The mail server refused the message (code {exc.smtp_code})."
            ) from None
        except (smtplib.SMTPException, OSError) as exc:
            raise CommandError(
                f"Could not reach the mail server at {settings.EMAIL_HOST}:{settings.EMAIL_PORT} "
                f"({type(exc).__name__}). Check EMAIL_HOST, EMAIL_PORT and EMAIL_USE_TLS."
            ) from None
        self.stdout.write(
            self.style.SUCCESS(
                f"Accepted by {settings.EMAIL_HOST}:{settings.EMAIL_PORT}. Check the inbox."
            )
        )
