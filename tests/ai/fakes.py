from gauge.ai.claude import JsonResult


class FakeLLM:
    """Returns queued results and records every prompt it was sent."""

    model = "claude-opus-5"

    def __init__(self, *results: JsonResult) -> None:
        self.results = list(results)
        self.calls: list[dict] = []

    def complete_json(self, system, user, schema, max_tokens=2048):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return self.results.pop(0)


def answer(
    decision: str, confidence: float, rationale: str = "Same address and topic."
) -> JsonResult:
    return JsonResult(
        {"decision": decision, "confidence": confidence, "rationale": rationale},
        model="claude-opus-5",
        request_id="req_test",
        stop_reason="end_turn",
    )
