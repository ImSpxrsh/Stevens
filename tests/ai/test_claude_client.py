import json
from types import SimpleNamespace

import anthropic
import httpx2

from gauge.ai.claude import FALLBACK_BETA, ClaudeJsonLLM


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def client(response=None, error=None):
    messages = FakeMessages(response, error)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def response(text, stop_reason="end_turn", model="claude-opus-5"):
    r = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason, model=model
    )
    r._request_id = "req_123"
    return r


SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}


def test_request_uses_structured_output_and_default_fallbacks(monkeypatch):
    monkeypatch.delenv("GAUGE_CLAUDE_MODEL", raising=False)
    fake, messages = client(response(json.dumps({"ok": True})))
    result = ClaudeJsonLLM(client=fake).complete_json("sys", "user", SCHEMA)
    assert result.ok and result.data == {"ok": True}
    assert result.request_id == "req_123"
    kw = messages.kwargs
    assert kw["model"] == "claude-opus-5"
    assert kw["betas"] == [FALLBACK_BETA] and kw["fallbacks"] == "default"
    assert kw["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert kw["system"] == "sys"


def test_model_and_effort_come_from_env(monkeypatch):
    monkeypatch.setenv("GAUGE_CLAUDE_MODEL", "claude-sonnet-5")
    monkeypatch.setenv("GAUGE_CLAUDE_EFFORT", "low")
    fake, messages = client(response("{}"))
    ClaudeJsonLLM(client=fake).complete_json("s", "u", SCHEMA)
    assert messages.kwargs["model"] == "claude-sonnet-5"
    assert messages.kwargs["output_config"]["effort"] == "low"


def test_served_model_is_reported_after_fallback():
    fake, _ = client(response("{}", model="claude-opus-4-8"))
    assert ClaudeJsonLLM(client=fake).complete_json("s", "u", SCHEMA).model == "claude-opus-4-8"


def test_refusal_truncation_and_bad_json_become_errors():
    for resp, err in (
        (response("{}", stop_reason="refusal"), "refusal"),
        (response('{"a":', stop_reason="max_tokens"), "max_tokens"),
        (response("not json"), "invalid_json"),
        (response("[1, 2]"), "invalid_json"),
    ):
        fake, _ = client(resp)
        result = ClaudeJsonLLM(client=fake).complete_json("s", "u", SCHEMA)
        assert not result.ok and result.error == err


def test_api_failures_become_errors_not_exceptions():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    fake, _ = client(error=anthropic.APIConnectionError(request=request))
    assert ClaudeJsonLLM(client=fake).complete_json("s", "u", SCHEMA).error == "connection_error"
    resp = httpx2.Response(500, request=request)
    fake, _ = client(error=anthropic.InternalServerError("boom", response=resp, body=None))
    assert ClaudeJsonLLM(client=fake).complete_json("s", "u", SCHEMA).error == "api_error_500"
