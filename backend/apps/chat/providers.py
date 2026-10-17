"""The single place that talks to an AI provider.

Everything else calls `get_provider().complete(...)` and handles three outcomes: text,
`ProviderRefused`, or `ProviderUnavailable`. Swapping providers means adding a class
here and naming it in CHAT_PROVIDER. Nothing in this file logs a prompt or a reply.

Data minimization: a provider receives the fixed instructions, a few reviewed
passages and the conversation text, plus a short wellbeing summary only if the
student turned that on (apps/chat/context.py). It never receives a name, an email
address, a user id, a Vent entry or a contact.
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


class OpenAICompatibleProvider:
    """Any server that speaks the OpenAI chat-completions API. Uses only the standard library.

    One class covers both modes: a free model on your own machine through Ollama
    (LLM_BASE_URL=http://localhost:11434/v1, no key) and a hosted provider for the
    public demo, such as Groq or OpenRouter (their /v1 URL plus LLM_API_KEY). The key is
    read from settings on the server and is never sent to the browser.
    """

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        base = settings.LLM_BASE_URL.rstrip("/")
        if not base.startswith(("http://", "https://")):
            logger.error("chat_provider_misconfigured")
            raise ProviderUnavailable
        body: dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0.8,
            "max_tokens": settings.CHAT_MAX_OUTPUT_TOKENS,
            "stream": False,
        }
        # Reasoning models (such as gpt-oss on Groq) think before answering. A low
        # effort keeps replies quick; their reasoning is returned outside `content`.
        if settings.LLM_REASONING_EFFORT:
            body["reasoning_effort"] = settings.LLM_REASONING_EFFORT
        # A named client: some hosted APIs sit behind Cloudflare, which rejects the
        # default "Python-urllib" user agent with a 403.
        headers = {"Content-Type": "application/json", "User-Agent": "mirrorspace/1.0"}
        if settings.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            f"{base}/chat/completions",
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            # The scheme is checked above, so only http and https are ever opened.
            with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT) as response:  # noqa: S310
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            # Status code only: the error body can echo the request.
            logger.error("chat_provider_error", extra={"status": error.code})
            raise ProviderUnavailable from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            logger.warning("chat_provider_unreachable")
            raise ProviderUnavailable from None
        try:
            text = str(payload["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderUnavailable from None
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
