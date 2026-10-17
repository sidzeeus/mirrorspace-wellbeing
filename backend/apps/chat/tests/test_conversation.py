"""Free conversation (decision B74) and the OpenAI-compatible provider."""

from __future__ import annotations

import io
import json
import logging
import urllib.error

import pytest

from apps.chat import policy, services
from apps.chat.providers import MockProvider, OpenAICompatibleProvider, ProviderUnavailable
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

CANARY = "CANARY-ollama-private-words"


@pytest.fixture(autouse=True)
def _reset():
    MockProvider.reset()
    yield
    MockProvider.reset()


@pytest.fixture
def student():
    return UserFactory(display_name="Asha Rao")


class TestFreeConversation:
    def test_a_message_with_no_reviewed_material_still_gets_a_conversational_reply(self, student):
        MockProvider.script = "That sounds like a long day. What has been on your mind?"
        reply = services.generate_reply(student, "hello, I feel kind of lonely today")
        assert reply.kind == services.ANSWER
        assert reply.text.startswith("That sounds like a long day")
        assert reply.sources == []
        assert len(MockProvider.calls) == 1
        system = MockProvider.calls[0]["system"]
        assert "supportive listener" in system
        assert "<passage" not in system

    def test_reviewed_material_is_offered_when_it_matches(self, student):
        from apps.chat.knowledge import index_document
        from apps.chat.models import ContentDocument

        document = ContentDocument.objects.create(
            slug="sleep",
            title="Sleep basics",
            source="test",
            body="Most students need seven to nine hours of sleep. Regular sleep times help.",
            review_status="approved",
        )
        index_document(document)
        reply = services.generate_reply(student, "how many hours of sleep do students need")
        assert "<passage" in MockProvider.calls[0]["system"]
        assert [source["title"] for source in reply.sources] == ["Sleep basics"]

    def test_crisis_wording_still_never_reaches_the_model(self, student):
        reply = services.generate_reply(student, "I want to kill myself")
        assert reply.kind == services.SAFETY
        assert MockProvider.calls == []

    def test_the_model_reply_is_still_checked(self, student):
        MockProvider.script = "You have depression. Take sertraline 50 mg."
        reply = services.generate_reply(student, "I feel flat")
        assert reply.kind == services.OFF_POLICY

    def test_memory_covers_a_real_conversation(self, student):
        history = []
        for i in range(12):
            history += [
                {"role": "user", "content": f"message {i}"},
                {"role": "assistant", "content": f"reply {i}"},
            ]
        services.generate_reply(student, "and one more thing", history)
        sent = MockProvider.calls[0]["messages"]
        assert services.MAX_HISTORY_TURNS >= 20
        assert len(sent) == services.MAX_HISTORY_TURNS + 1
        assert sent[-1] == {"role": "user", "content": "and one more thing"}

    def test_instructions_keep_the_rules(self):
        prompt = policy.build_system_prompt([])
        for rule in ("not a therapist", "Diagnose", "medication", "monitoring", "Support"):
            assert rule in prompt


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestOpenAICompatibleProvider:
    def _capture(self, monkeypatch, reply="Hello there.", error=None):
        sent = {}

        def fake_urlopen(request, timeout):
            sent["url"] = request.full_url
            sent["body"] = json.loads(request.data)
            sent["timeout"] = timeout
            sent["headers"] = dict(request.header_items())
            if error is not None:
                raise error
            return FakeResponse(
                json.dumps(
                    {"choices": [{"message": {"role": "assistant", "content": reply}}]}
                ).encode()
            )

        monkeypatch.setattr("apps.chat.providers.urllib.request.urlopen", fake_urlopen)
        return sent

    def test_sends_only_instructions_and_conversation(self, monkeypatch, settings):
        settings.LLM_BASE_URL = "http://ollama.test:11434/v1"
        settings.LLM_MODEL = "llama3.1:8b"
        settings.LLM_API_KEY = ""
        sent = self._capture(monkeypatch)
        text = OpenAICompatibleProvider().complete(
            system="be kind", messages=[{"role": "user", "content": "hi"}]
        )
        assert text == "Hello there."
        assert sent["url"] == "http://ollama.test:11434/v1/chat/completions"
        assert "Authorization" not in sent["headers"]
        body = sent["body"]
        assert body["model"] == "llama3.1:8b"
        assert body["stream"] is False
        assert body["messages"] == [
            {"role": "system", "content": "be kind"},
            {"role": "user", "content": "hi"},
        ]
        assert set(body) == {"model", "messages", "stream", "temperature", "max_tokens"}

    @pytest.mark.parametrize(
        "error",
        [
            urllib.error.URLError("refused"),
            TimeoutError(),
            urllib.error.HTTPError("http://x", 500, "boom", {}, None),
        ],
    )
    def test_any_failure_is_reported_as_unavailable_and_logs_no_text(
        self, monkeypatch, caplog, error
    ):
        caplog.set_level(logging.DEBUG)
        self._capture(monkeypatch, error=error)
        with pytest.raises(ProviderUnavailable):
            OpenAICompatibleProvider().complete(
                system="rules", messages=[{"role": "user", "content": CANARY}]
            )
        assert CANARY not in caplog.text

    def test_a_hosted_provider_gets_the_key_as_a_bearer_token(self, monkeypatch, settings):
        settings.LLM_BASE_URL = "https://api.groq.test/openai/v1/"
        settings.LLM_API_KEY = "test-key-not-real"
        sent = self._capture(monkeypatch)
        OpenAICompatibleProvider().complete(
            system="s", messages=[{"role": "user", "content": "hi"}]
        )
        assert sent["url"] == "https://api.groq.test/openai/v1/chat/completions"
        assert sent["headers"]["Authorization"] == "Bearer test-key-not-real"

    def test_a_non_http_url_is_refused(self, monkeypatch, settings):
        settings.LLM_BASE_URL = "file:///etc/passwd"
        self._capture(monkeypatch)
        with pytest.raises(ProviderUnavailable):
            OpenAICompatibleProvider().complete(system="s", messages=[])

    def test_a_malformed_reply_counts_as_unavailable(self, monkeypatch):
        def fake_urlopen(request, timeout):
            return FakeResponse(b'{"unexpected": true}')

        monkeypatch.setattr("apps.chat.providers.urllib.request.urlopen", fake_urlopen)
        with pytest.raises(ProviderUnavailable):
            OpenAICompatibleProvider().complete(system="s", messages=[])

    def test_an_empty_reply_counts_as_unavailable(self, monkeypatch):
        self._capture(monkeypatch, reply="   ")
        with pytest.raises(ProviderUnavailable):
            OpenAICompatibleProvider().complete(
                system="rules", messages=[{"role": "user", "content": "hi"}]
            )
