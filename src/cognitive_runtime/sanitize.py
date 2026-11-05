"""Rejection of answer-side and self-asserted-trust fields.

Callers cannot grant trust by writing a flag: ``verified`` and ``gold`` style
keys are refused at the boundary, so a forged field cannot reach the gate.
"""

from __future__ import annotations

import re
from typing import Any

FORBIDDEN_KEYS = frozenset(
    {
        "gold",
        "gold_answer",
        "answer_key",
        "answer",
        "expected",
        "expected_answer",
        "label_truth",
        "ground_truth",
        "verified",
        "is_verified",
        "outcome_verified",
        "trusted",
        "promotion_state",
    }
)

_FORBIDDEN_PATTERN = re.compile(r"(gold|answer.?key|ground.?truth|expected|verified|trusted)", re.I)


class ForbiddenInput(ValueError):
    """Input carries answer-side or self-asserted trust information."""


def scan(value: Any, path: str = "$") -> list[str]:
    """Return the JSON paths that carry forbidden keys."""
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            location = f"{path}.{key}"
            if key in FORBIDDEN_KEYS or _FORBIDDEN_PATTERN.search(str(key)):
                findings.append(location)
            findings.extend(scan(nested, location))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(scan(nested, f"{path}[{index}]"))
    return findings


def ensure_clean(value: Any) -> None:
    findings = scan(value)
    if findings:
        raise ForbiddenInput(f"forbidden keys in input: {', '.join(sorted(findings))}")
