"""The single place that talks to an AI provider.

Everything else calls `get_provider().complete(...)` and handles three outcomes: text,
`ProviderRefused`, or `ProviderUnavailable`. Swapping providers means adding a class
here and naming it in CHAT_PROVIDER. Nothing in this file logs a prompt or a reply.

Data minimization: a provider receives the fixed instructions, a few reviewed
passages, and the conversation text. It never receives a name, an email address, a
user id, a check-in, a safety plan or a contact.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Protocol

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class ProviderUnavailable(Exception):
    """The provider could not answer: outage, timeout, rate limit, bad configuration."""


class ProviderRefused(Exception):
    """The provider declined to answer this request."""


class Provider(Protocol):
    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str: ...


class MockProvider:
    """A stand-in for tests and local development. It never leaves the process.

    It answers by quoting the first reviewed passage it was given, which is enough to
    exercise the whole pipeline. Tests also script it (`MockProvider.script`) to
    simulate an outage, a refusal, or a model that misbehaves.
    """

    script: Any = None
    calls: list[dict[str, Any]] = []

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        type(self).calls.append({"system": system, "messages": messages})
        script = type(self).script
        if isinstance(script, Exception):
            raise script
        if callable(script):
            return str(script(system=system, messages=messages))
        if isinstance(script, str):
            return script
        marker = "<passage"
        if marker in system:
            body = system.split(marker, 1)[1].split(">", 1)[1].split("</passage>", 1)[0]
            first = body.strip().split(". ")[0].strip().rstrip(".")
            return f"From the reviewed material: {first}."
        return "I do not have reviewed material on that."

    @classmethod
    def reset(cls) -> None:
        cls.script = None
        cls.calls = []


class AnthropicProvider:
    """Claude through the official Anthropic SDK.

    The API key is read by the SDK from the environment (ANTHROPIC_API_KEY); it is
    never passed around in code or settings. Thinking is always on for this model, so
    depth is set with `effort`: answers here are short and grounded, so it is "low".
    If the model's safety system declines a request, `fallbacks="default"` lets the API
    re-run it on Anthropic's recommended fallback model inside the same call.
    """

    def __init__(self) -> None:
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(timeout=settings.CHAT_PROVIDER_TIMEOUT, max_retries=1)

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        anthropic = self._anthropic
        try:
            response = self._client.beta.messages.create(
                model=settings.CHAT_MODEL,
                max_tokens=settings.CHAT_MAX_OUTPUT_TOKENS,
                system=system,
                messages=messages,
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # type: ignore[call-overload]
            )
        except anthropic.RateLimitError:
            logger.warning("chat_provider_rate_limited")
            raise ProviderUnavailable from None
        except anthropic.APIStatusError as error:
            # Status code only. The message can echo request content.
            logger.error("chat_provider_error", extra={"status": error.status_code})
            raise ProviderUnavailable from None
        except anthropic.APIConnectionError:
            logger.warning("chat_provider_unreachable")
            raise ProviderUnavailable from None

        if response.stop_reason == "refusal":
            raise ProviderRefused
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise ProviderUnavailable
        return text


class OllamaProvider:
    """A model running on our own machine through Ollama (https://ollama.com). Free.

    Nothing leaves the server the app runs on: the request goes to the Ollama server
    named by OLLAMA_URL, which runs OLLAMA_MODEL locally. Uses only the standard library.
    """

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        body = {
            "model": settings.OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            # Keep the model loaded between messages, so replies after the first are quick.
            "keep_alive": "30m",
            "options": {"temperature": 0.7, "num_predict": settings.CHAT_MAX_OUTPUT_TOKENS},
        }
        base = settings.OLLAMA_URL.rstrip("/")
        if not base.startswith(("http://", "https://")):
            logger.error("chat_provider_misconfigured")
            raise ProviderUnavailable
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            f"{base}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            # The scheme is checked above, so only http and https are ever opened.
            with urllib.request.urlopen(request, timeout=settings.OLLAMA_TIMEOUT) as response:  # noqa: S310
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            logger.error("chat_provider_error", extra={"status": error.code})
            raise ProviderUnavailable from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            logger.warning("chat_provider_unreachable")
            raise ProviderUnavailable from None
        text = str((payload.get("message") or {}).get("content") or "").strip()
        if not text:
            raise ProviderUnavailable
        return text


_instance: Provider | None = None


def get_provider() -> Provider:
    global _instance  # noqa: PLW0603 - one client per process
    if _instance is None:
        _instance = import_string(settings.CHAT_PROVIDER)()
    return _instance


def reset_provider() -> None:
    global _instance  # noqa: PLW0603
    _instance = None
