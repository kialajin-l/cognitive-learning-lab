"""The boundary between an untrusted model proposal and final state."""

from __future__ import annotations

from typing import Any

from .judgment import RuleDecision


def compose_boundary(
    *,
    judgment: RuleDecision,
    candidates: list[str],
    raw_proposal: Any = None,
    proposal_text: Any = None,
) -> dict[str, Any]:
    """Keep raw proposal, judgment and authorised output as three separate layers."""
    allowed = judgment.status == "allow" and judgment.selected in candidates
    return {
        "raw_proposal": raw_proposal,
        "judgment_output": judgment.as_dict(),
        "final_output": {
            "status": "answered" if allowed else "abstained",
            "selected": judgment.selected if allowed else None,
            "authorization": "verified_judgment" if allowed else "none",
        },
        "memory_writeback": {
            "allowed": allowed,
            "reason": "verified_judgment_allow" if allowed else f"judgment_{judgment.reason}",
        },
        "proposal_agrees_with_judgment": (
            raw_proposal is not None and allowed and proposal_text == judgment.selected
        ),
    }
