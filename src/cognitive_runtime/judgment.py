"""Fail-closed typed judgment over verified structured rules.

Laya may propose a candidate, but a proposal never authorises an answer: only a
rule that came from promoted, hash-intact memory can. Ambiguity, conflict,
duplicate provenance or a missing rule all abstain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .memory.store import MemoryRecord
from .sources import expected_content


@dataclass(frozen=True)
class RuleDecision:
    status: str
    selected: str | None
    reason: str
    matched_rule_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected": self.selected,
            "reason": self.reason,
            "matched_rule_ids": list(self.matched_rule_ids),
        }


def rules_from_memories(records: Iterable[MemoryRecord]) -> list[dict[str, Any]]:
    """Derive candidate rules from memory, keeping trust state visible to the gate."""
    rules: list[dict[str, Any]] = []
    for record in records:
        assignment = assignment_of(record.content)
        if assignment is None or record.promotion_state != "promoted":
            continue
        rules.append(
            {
                "rule_id": record.memory_id,
                "entity_scope": record.entity,
                "assignment": assignment,
                "source": record.source,
                "source_ref": record.source_ref,
                "verification_status": record.verification_status,
                "content_sha256": record.content_sha256,
            }
        )
    return rules


def assignment_of(content: str) -> str | None:
    """Extract the label from the canonical assignment sentence."""
    marker = " is assigned to "
    if marker not in content or not content.startswith("Directory record: "):
        return None
    tail = content[len("Directory record: ") :].split(marker, 1)
    if len(tail) != 2:
        return None
    return tail[1].rstrip(".")


def build_content(entity: str, label: str) -> str:
    return expected_content(entity, label)


def select_rule(
    *,
    entity: str,
    candidates: Iterable[str],
    rules: Iterable[dict[str, Any]],
) -> RuleDecision:
    candidate_set = tuple(candidates)
    if not candidate_set or len(candidate_set) != len(set(candidate_set)):
        return RuleDecision("abstain", None, "invalid_candidate_set")

    matches = []
    for rule in rules:
        if rule.get("entity_scope") != entity:
            continue
        if rule.get("verification_status") != "pass":
            return RuleDecision("abstain", None, "unverified_matching_rule")
        if rule.get("promotion_state", "promoted") != "promoted":
            continue
        if rule.get("assignment") not in candidate_set:
            continue
        matches.append(rule)

    if not matches:
        return RuleDecision("abstain", None, "no_verified_matching_rule")

    ids = tuple(sorted(str(rule["rule_id"]) for rule in matches))
    assignments = {rule["assignment"] for rule in matches}
    if len(assignments) != 1:
        return RuleDecision("abstain", None, "conflicting_verified_rules", ids)
    if len(matches) > 1 and len({rule.get("source_ref") for rule in matches}) != len(matches):
        return RuleDecision("abstain", None, "duplicate_rule_source", ids)
    return RuleDecision("allow", next(iter(assignments)), "verified_rule_match", ids)
