"""Proposal providers.

Two implementations share one contract: :class:`~cognitive_runtime.model.laya.LayaProvider`
is the formal path and :class:`~cognitive_runtime.model.mock.MockProvider` is an
offline stand-in. ``provider_class`` is carried on every result so a report can
never silently mix the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

STATUSES = ("ok", "abstain", "schema_failure", "timeout", "runtime_error")


@dataclass
class Proposal:
    """A model's typed choice over candidate ids. Never an authorisation."""

    status: str
    selected: str | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    model_id: str = "none"
    model_digest: str = "none"
    provider_class: str = "mock"
    calibration_status: str = "unknown"
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    retries: int = 0
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected": self.selected,
            "probabilities": self.probabilities,
            "confidence": self.confidence,
            "model_id": self.model_id,
            "model_digest": self.model_digest,
            "provider_class": self.provider_class,
            "calibration_status": self.calibration_status,
            "cost": {
                "latency_ms": self.latency_ms,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "retries": self.retries,
            },
            "error": self.error,
        }


class DecisionProvider(Protocol):
    provider_class: str

    def propose(self, *, state: str, questions: dict[str, dict[str, Any]]) -> Proposal:
        ...
