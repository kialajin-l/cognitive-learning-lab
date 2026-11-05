"""Offline stand-in provider.

Mock output is labelled ``provider_class="mock"`` everywhere it travels, so a
mock run cannot be read as model evidence. It is for tests and for ``doctor``
only; acceptance items that require a real model call are not satisfied by it.
"""

from __future__ import annotations

from ..prompting import QUESTION_ID
from .base import Proposal


class MockProvider:
    provider_class = "mock"
    model_id = "mock:scripted-choice"
    model_digest = "mock:scripted-choice@1"

    def __init__(self, *, choice: str | None = None, confidence: float = 0.0) -> None:
        self.choice = choice
        self.confidence = confidence

    def propose(self, *, state: str, questions: dict[str, dict[str, object]]) -> Proposal:
        payload = questions.get(QUESTION_ID) or {}
        criteria = payload.get("criteria") or {}
        if not isinstance(criteria, dict) or not criteria:
            return Proposal(
                status="schema_failure",
                provider_class=self.provider_class,
                model_id=self.model_id,
                model_digest=self.model_digest,
                error={"code": "schema_failure", "message": "no candidates"},
            )
        selected = self.choice if self.choice in criteria else next(iter(sorted(criteria)))
        uniform = round(1.0 / len(criteria), 6)
        return Proposal(
            status="ok",
            selected=selected,
            probabilities={key: uniform for key in criteria},
            confidence=self.confidence,
            model_id=self.model_id,
            model_digest=self.model_digest,
            provider_class=self.provider_class,
            calibration_status="not_applicable",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
        )
