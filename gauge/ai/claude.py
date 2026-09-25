"""A narrow Claude client: one request, one JSON object back.

Every Gauge LLM feature goes through ``JsonLLM`` so tests can substitute a
fake and so every call returns the audit fields we store (served model,
request id, stop reason). Any failure (API error, refusal, truncation,
invalid JSON) comes back as ``JsonResult.error`` instead of raising; callers
treat that as "no decision" and leave the item for a person.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_EFFORT = "medium"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class JsonResult:
    data: dict[str, Any] | None
    model: str  # the model that actually served the request
    request_id: str | None = None
    stop_reason: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.data is not None


class JsonLLM(Protocol):
    model: str

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int = 2048
    ) -> JsonResult: ...


class ClaudeJsonLLM:
    """``JsonLLM`` backed by the Anthropic API with structured outputs.

    Model and effort come from ``GAUGE_CLAUDE_MODEL`` / ``GAUGE_CLAUDE_EFFORT``
    (see ``.env.example``). Credentials are resolved by the SDK
    (``ANTHROPIC_API_KEY`` or an ``ant auth login`` profile) and never logged.
    """

    def __init__(self, model: str | None = None, effort: str | None = None, client=None):
        import anthropic  # optional dependency: pip install -e ".[ai]"

        self._anthropic = anthropic
        self.model = model or os.environ.get("GAUGE_CLAUDE_MODEL") or DEFAULT_MODEL
        self.effort = effort or os.environ.get("GAUGE_CLAUDE_EFFORT") or DEFAULT_EFFORT
        self._client = client or anthropic.Anthropic()

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int = 2048
    ) -> JsonResult:
        a = self._anthropic
        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except a.RateLimitError:
            return JsonResult(None, self.model, error="rate_limited")
        except a.APIStatusError as e:
            return JsonResult(None, self.model, error=f"api_error_{e.status_code}")
        except a.APIConnectionError:
            return JsonResult(None, self.model, error="connection_error")

        served = getattr(response, "model", None) or self.model
        request_id = getattr(response, "_request_id", None)
        if response.stop_reason in ("refusal", "max_tokens"):
            return JsonResult(None, served, request_id, response.stop_reason, response.stop_reason)
        text = next((b.text for b in response.content if b.type == "text"), None)
        try:
            data = json.loads(text) if text is not None else None
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict):
            return JsonResult(None, served, request_id, response.stop_reason, "invalid_json")
        return JsonResult(data, served, request_id, response.stop_reason)
