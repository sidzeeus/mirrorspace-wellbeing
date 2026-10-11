"""Health probes, API defaults, the OpenAPI schema and production configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent

PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "x" * 64 + "-Aa1!-only-for-the-deploy-check",
    "DJANGO_ALLOWED_HOSTS": "api.example.test",
    "FRONTEND_URL": "https://app.example.test",
    "DATABASE_URL": "postgres://u:p@db.example.test:5432/app",
    "REDIS_URL": "rediss://redis.example.test:6379/0",
    "CSRF_TRUSTED_ORIGINS": "https://app.example.test",
    "CORS_ALLOWED_ORIGINS": "https://app.example.test",
    "DEFAULT_FROM_EMAIL": "no-reply@example.test",
    "FIELD_ENCRYPTION_KEYS": "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=",
}


def manage(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    base = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("DJANGO_", "DATABASE_", "FIELD_", "SHOW_"))
    }
    return subprocess.run(  # noqa: S603 - fixed arguments, our own manage.py
        [sys.executable, "manage.py", *args],
        cwd=BACKEND_DIR,
        env={**base, **env},
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestHealth:
    def test_liveness_needs_no_sign_in(self, api_client):
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.django_db
    def test_readiness_reports_components(self, api_client):
        response = api_client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "checks": {"database": True, "cache": True}}

    @pytest.mark.django_db
    def test_readiness_fails_closed_without_details(self, api_client, monkeypatch):
        monkeypatch.setattr("config.health._database_ok", lambda: False)
        response = api_client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json() == {
            "status": "unavailable",
            "checks": {"database": False, "cache": True},
        }

    def test_probes_are_not_rate_limited(self, api_client):
        for _ in range(80):
            assert api_client.get("/api/v1/health").status_code == 200


@pytest.mark.django_db
class TestApiDefaults:
    def test_authentication_is_required_by_default(self):
        assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
            "rest_framework.permissions.IsAuthenticated"
        ]
        assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
            "config.api.SessionAuth"
        ]

    def test_throttles_and_pagination_are_set(self):
        rest = settings.REST_FRAMEWORK
        assert rest["DEFAULT_THROTTLE_CLASSES"]
        assert {"anon", "user", "login"} <= set(rest["DEFAULT_THROTTLE_RATES"])
        assert rest["DEFAULT_PAGINATION_CLASS"] == "config.api.DefaultPagination"

    def test_only_json_is_accepted_and_returned(self):
        rest = settings.REST_FRAMEWORK
        assert rest["DEFAULT_PARSER_CLASSES"] == ["rest_framework.parsers.JSONParser"]
        assert rest["DEFAULT_RENDERER_CLASSES"] == ["rest_framework.renderers.JSONRenderer"]

    def test_anonymous_requests_are_rate_limited(self, api_client):
        statuses = [api_client.get("/api/v1/auth/csrf").status_code for _ in range(61)]
        assert statuses[0] == 200
        assert statuses[-1] == 429

    def test_cors_allows_only_the_frontend_origin(self, api_client):
        allowed = api_client.get("/api/v1/health", HTTP_ORIGIN=settings.FRONTEND_URL)
        denied = api_client.get("/api/v1/health", HTTP_ORIGIN="https://evil.example.test")
        assert allowed.headers["Access-Control-Allow-Origin"] == settings.FRONTEND_URL
        assert allowed.headers["Access-Control-Allow-Credentials"] == "true"
        assert "Access-Control-Allow-Origin" not in denied.headers

    def test_cors_is_never_a_wildcard(self):
        assert not getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
        assert "*" not in settings.CORS_ALLOWED_ORIGINS

    def test_oversized_request_is_rejected(self, api_client):
        body = '{"email": "' + "a" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 10) + '"}'
        response = api_client.post("/api/v1/auth/login", data=body, content_type="application/json")
        assert response.status_code in (400, 413)


@pytest.mark.django_db
class TestSchema:
    def test_schema_endpoint_lists_the_routes(self, api_client):
        response = api_client.get("/api/v1/schema", HTTP_ACCEPT="application/json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        for route in (
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/me",
            "/api/v1/auth/password-reset",
            "/api/v1/account",
            "/api/v1/health",
        ):
            assert route in paths

    def test_schema_generates_without_warnings(self):
        result = manage(
            "spectacular",
            "--validate",
            "--fail-on-warn",
            "--file",
            os.devnull,
            env={"DJANGO_SETTINGS_MODULE": "config.settings.test"},
        )
        assert result.returncode == 0, result.stderr


class TestProductionSettings:
    def test_deploy_check_passes_with_no_warnings(self):
        result = manage("check", "--deploy", "--fail-level", "WARNING", env=PRODUCTION_ENV)
        assert result.returncode == 0, result.stdout + result.stderr

    @pytest.mark.parametrize(
        "missing",
        [
            "DJANGO_SECRET_KEY",
            "DJANGO_ALLOWED_HOSTS",
            "DATABASE_URL",
            "REDIS_URL",
            "FIELD_ENCRYPTION_KEYS",
        ],
    )
    def test_refuses_to_start_without_required_variables(self, missing):
        env = {k: v for k, v in PRODUCTION_ENV.items() if k != missing}
        result = manage("check", env=env)
        assert result.returncode != 0
        assert missing in result.stderr

    def test_debug_is_off_and_schema_is_private(self):
        code = (
            "from django.conf import settings as s;"
            "assert s.DEBUG is False;"
            "assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE;"
            "assert s.SPECTACULAR_SETTINGS['SERVE_PERMISSIONS'] == "
            "['rest_framework.permissions.IsAdminUser'];"
            "print('ok')"
        )
        result = manage("shell", "-c", code, env=PRODUCTION_ENV)
        assert result.returncode == 0, result.stderr
