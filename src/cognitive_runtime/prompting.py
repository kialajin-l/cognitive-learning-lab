"""Turn a decision input into the model's state string and typed option set.

Answer-side information never enters either: the model sees the question, the
constraints and bounded memory evidence, and picks among candidate ids.
"""

from __future__ import annotations

from typing import Any

QUESTION_ID = "sel"
MAX_CANDIDATES = 20


class QuestionBuildError(ValueError):
    """The decision input cannot be turned into a typed choice."""


def build_questions(decision_input: dict[str, Any], *, canonicalize: bool = True) -> dict[str, dict[str, Any]]:
    candidates = decision_input.get("candidates") or []
    if not isinstance(candidates, list) or not candidates:
        raise QuestionBuildError("candidates must be a non-empty list")
    if len(candidates) > MAX_CANDIDATES:
        raise QuestionBuildError(f"{len(candidates)} candidates exceed the option budget of {MAX_CANDIDATES}")

    ordered = sorted(candidates, key=lambda item: str(item.get("candidate_id", ""))) if canonicalize else candidates
    criteria: dict[str, str] = {}
    for candidate in ordered:
        candidate_id = candidate.get("candidate_id")
        text = candidate.get("text")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise QuestionBuildError("each candidate needs a non-empty candidate_id")
        if not isinstance(text, str):
            raise QuestionBuildError(f"candidate {candidate_id} text must be a string")
        criteria[candidate_id] = text

    question = str(decision_input.get("question") or "").strip()
    if not question:
        raise QuestionBuildError("question must be a non-empty string")
    instructions = f"Question: {question}\nSelect the single best candidate."
    constraints = decision_input.get("constraints") or []
    if constraints:
        instructions = f"{instructions}\nConstraints: {'; '.join(str(item) for item in constraints)}"
    instructions = f"{instructions}\nAnswer with exactly one of the options below."
    return {QUESTION_ID: {"type": "choice", "instructions": instructions, "criteria": criteria}}


def build_state(decision_input: dict[str, Any]) -> str:
    parts = [str(decision_input.get("question") or "").strip()]
    constraints = decision_input.get("constraints") or []
    if constraints:
        parts.append("Constraints: " + "; ".join(str(item) for item in constraints))
    evidence = decision_input.get("memory_evidence") or []
    if evidence:
        rendered = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            semantic = item.get("content") or item.get("text")
            if isinstance(semantic, str) and semantic.strip():
                rendered.append(f"{item.get('fact_id')}={item.get('support')}: {semantic.strip()[:200]}")
            else:
                rendered.append(f"{item.get('fact_id')}={item.get('support')}")
        if rendered:
            parts.append("Memory evidence (fact_id=support): " + ", ".join(rendered))
    return "\n".join(part for part in parts if part)
