"""Source receipts and the verification layer that reads them.

Verification here is ``source-consistency-v1``: it proves a memory record still
matches the source receipt it cites. It does **not** prove the cited claim is
true in the world, and the API never returns a status that suggests otherwise.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hashing import sha256_text

SENTENCE_TEMPLATE = "Directory record: {entity} is assigned to {label}."


def expected_content(entity: str, label: str) -> str:
    return SENTENCE_TEMPLATE.format(entity=entity, label=label)


@dataclass(frozen=True)
class SourceRecord:
    ref: str
    entity: str
    label: str
    captured_at: str

    @property
    def content(self) -> str:
        return expected_content(self.entity, self.label)

    @property
    def content_sha256(self) -> str:
        return sha256_text(self.content)


class SourceRegistry:
    """Append-only local receipts; the only thing the verifier is allowed to trust."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._records: dict[str, SourceRecord] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                self._records[payload["ref"]] = SourceRecord(
                    ref=payload["ref"],
                    entity=payload["entity"],
                    label=payload["label"],
                    captured_at=payload.get("captured_at", "unknown"),
                )

    def lookup(self, ref: str) -> SourceRecord | None:
        return self._records.get(ref)

    def refs(self) -> list[str]:
        return sorted(self._records)


@dataclass(frozen=True)
class VerificationResult:
    status: str
    detail: str
    verification_type: str = "source-consistency-v1"
    checked_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "verification_type": self.verification_type,
            "status": self.status,
            "detail": self.detail,
            "checked_ref": self.checked_ref,
        }


def verify_record(entry: Any, registry: SourceRegistry) -> VerificationResult:
    """Check one memory record against the receipt it cites."""
    source_ref = getattr(entry, "source_ref", None) or (entry.get("source_ref") if isinstance(entry, dict) else None)
    content = getattr(entry, "content", None) or (entry.get("content") if isinstance(entry, dict) else None)
    entity = getattr(entry, "entity", None) or (entry.get("entity") if isinstance(entry, dict) else None)
    stored_hash = getattr(entry, "content_sha256", None) or (entry.get("content_sha256") if isinstance(entry, dict) else None)

    if not source_ref:
        return VerificationResult("fail", "missing_source_ref")
    receipt = registry.lookup(source_ref)
    if receipt is None:
        return VerificationResult("fail", f"unknown_source_ref:{source_ref}", checked_ref=source_ref)
    if stored_hash != sha256_text(content):
        return VerificationResult("fail", "content_hash_mismatch", checked_ref=source_ref)
    if content != receipt.content:
        return VerificationResult("fail", "content_mismatch_vs_receipt", checked_ref=source_ref)
    if entity != receipt.entity:
        return VerificationResult("fail", "entity_mismatch_vs_receipt", checked_ref=source_ref)
    return VerificationResult("pass", "content_matches_cited_receipt", checked_ref=source_ref)


@dataclass(frozen=True)
class LineageVerification:
    """Verification of a conclusion derived from already-trusted memory.

    The derived record cites its parents instead of a receipt, so the check is
    "every parent is still promoted, still hash-intact, and still says the same
    label". It inherits the parents' provenance and adds no new factual
    support, which is why the detail string says so.
    """

    status: str
    detail: str
    verification_type: str = "lineage-consistency-v1"
    parents: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "verification_type": self.verification_type,
            "status": self.status,
            "detail": self.detail,
            "parents": list(self.parents),
        }


def verify_derived(record: Any, parents: list[Any]) -> LineageVerification:
    from .judgment import assignment_of

    if not parents:
        return LineageVerification("fail", "no_parent_records")
    label = assignment_of(record.content)
    if label is None:
        return LineageVerification("fail", "derived_content_not_an_assignment")
    for parent in parents:
        if parent.promotion_state != "promoted":
            return LineageVerification("fail", f"parent_not_promoted:{parent.memory_id}", parents=tuple(p.memory_id for p in parents))
        if parent.entity != record.entity:
            return LineageVerification("fail", f"parent_entity_mismatch:{parent.memory_id}", parents=tuple(p.memory_id for p in parents))
        if assignment_of(parent.content) != label:
            return LineageVerification("fail", f"parent_label_mismatch:{parent.memory_id}", parents=tuple(p.memory_id for p in parents))
    return LineageVerification(
        "pass",
        "derived_from_promoted_parents_no_new_support",
        parents=tuple(p.memory_id for p in parents),
    )
