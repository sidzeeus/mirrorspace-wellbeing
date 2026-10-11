"""View base classes shared by the apps."""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.views import APIView


@method_decorator(csrf_protect, name="dispatch")
class CsrfProtectedAPIView(APIView):
    """Enforces CSRF even for anonymous requests.

    DRF only checks CSRF once a session exists. Sign-in, registration and the
    email-link endpoints are called anonymously, so they opt in here.
    """
