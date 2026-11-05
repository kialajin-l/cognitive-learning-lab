"""One request through the whole chain: retrieve, acquire, verify, propose, judge, write back.

The order is the contract. A model proposal is computed after retrieval and is
never an input to authorisation; writeback happens only after the judgment
allows, and even then it lands as a candidate that must pass verification
before promotion.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from . import OUTPUT_SCHEMA_VERSION, SCHEMA_VERSION, VERIFICATION_TYPE
from .boundary import compose_boundary
from .config import RuntimeConfig
from .hashing import sha256_json
from .judgment import build_content, rules_from_memories, select_rule
from .memory.store import MemoryStore, PromotionUnauthorized
from .prompting import QuestionBuildError, build_questions, build_state
from .providers import build_provider
from .retrieval import retrieve
from .sanitize import ensure_clean
from .sources import SourceRegistry, verify_derived, verify_record


class RequestError(ValueError):
    """The request cannot be processed as typed input."""


# A proposal that never arrived is not the same event as a model that declined:
# `abstain` is a usable answer-shaped result, these three mean the call failed.
NOT_RUN_STATUSES = ("schema_failure", "timeout", "runtime_error")


class ProviderUnavailable(RuntimeError):
    """The provider produced no usable proposal, so this run must be reported as not-run."""

    def __init__(self, run_id: str, proposal: Any) -> None:
        super().__init__(f"provider {proposal.provider_class} returned status={proposal.status!r}")
        self.run_id = run_id
        self.proposal = proposal


def run_request(request: dict[str, Any], config: RuntimeConfig, *, provider: Any = None) -> dict[str, Any]:
    started = time.perf_counter()
    ensure_clean(request)

    entity = request.get("entity")
    question = request.get("question")
    candidates = request.get("candidates")
    if not isinstance(entity, str) or not entity:
        raise RequestError("entity must be a non-empty string")
    if not isinstance(question, str) or not question:
        raise RequestError("question must be a non-empty string")
    if not isinstance(candidates, list) or not candidates:
        raise RequestError("candidates must be a non-empty list")

    run_id = request.get("run_id") or f"run-{uuid4().hex[:12]}"
    store = MemoryStore(config.resolve_store_path(request.get("store")), namespace=config.namespace)
    registry = SourceRegistry(config.resolve_sources_path())

    # Integrity runs before anything can authorise: a record edited on disk since
    # it was promoted must be quarantined, not trusted, in this same request.
    integrity = store.integrity_check()

    model_calls = 0
    acquisition_calls = 0

    retrieval = retrieve(store, entity=entity, query=question)
    trusted = [record for record in retrieval.matched if record.promotion_state == "promoted"]

    writeback_receipt = {"attempted": False, "written": [], "promoted": [], "refused": []}
    if not trusted and request.get("acquire"):
        acquisition_calls = _acquire(store, registry, request["acquire"], writeback_receipt)

    # Re-read: acquisition may have promoted records, and a second process must see them.
    retrieval = retrieve(store, entity=entity, query=question)
    trusted = [record for record in retrieval.matched if record.promotion_state == "promoted"]

    evidence = [
        {
            "fact_id": record.memory_id,
            "support": 1.0,
            "content": record.content[:2000],
            "source": record.source,
            "source_ref": record.source_ref,
            "content_sha256": record.content_sha256,
        }
        for record in trusted
    ]
    decision_input = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "task_id": request.get("task_id", run_id),
        "question": question,
        "entity": entity,
        "candidates": candidates,
        "candidate_set_sha256": sha256_json([c.get("candidate_id") for c in candidates]),
        "constraints": request.get("constraints") or [],
        "memory_evidence": evidence,
        "memory_snapshot_sha256": sha256_json(evidence),
    }

    try:
        state = build_state(decision_input)
        questions = build_questions(decision_input)
    except QuestionBuildError as exc:
        raise RequestError(str(exc)) from exc

    provider = provider or build_provider(config)
    proposal = provider.propose(state=state, questions=questions)
    model_calls += 1
    if proposal.status in NOT_RUN_STATUSES:
        raise ProviderUnavailable(run_id, proposal)

    rules = rules_from_memories(trusted)
    texts = [c.get("text") for c in candidates]
    judgment = select_rule(entity=entity, candidates=texts, rules=rules)
    boundary = compose_boundary(
        judgment=judgment,
        candidates=texts,
        raw_proposal=proposal.as_dict(),
        proposal_text=_text_of(candidates, proposal.selected),
    )

    if boundary["memory_writeback"]["allowed"] and judgment.selected is not None:
        conclusion = build_content(entity, judgment.selected)
        if not _already_stored(store, entity, conclusion):
            acquisition_calls += _writeback(store, entity, conclusion, list(judgment.matched_rule_ids), writeback_receipt)

    selected_id = next(
        (c.get("candidate_id") for c in candidates if c.get("text") == boundary["final_output"]["selected"]),
        None,
    )

    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "run_id": run_id,
        "status": boundary["final_output"]["status"],
        "selected": selected_id,
        "final_answer": boundary["final_output"]["selected"],
        "abstain_reason": None if selected_id else judgment.reason,
        "raw_proposal": boundary["raw_proposal"],
        "memory_hit": bool(trusted),
        "evidence_refs": [item["fact_id"] for item in evidence],
        "judgment": boundary["judgment_output"],
        "verification": {
            "type": VERIFICATION_TYPE,
            "scope": "provenance consistency, not external truth",
            "store_integrity": integrity,
        },
        "writeback": boundary["memory_writeback"],
        "writeback_receipt": writeback_receipt,
        "authorization": boundary["final_output"]["authorization"],
        "proposal_agrees_with_judgment": boundary["proposal_agrees_with_judgment"],
        "cost": {
            "model_calls": model_calls,
            "acquisition_calls": acquisition_calls,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "prompt_tokens": proposal.as_dict()["cost"]["prompt_tokens"],
            "completion_tokens": proposal.as_dict()["cost"]["completion_tokens"],
            "monetary_cost": None,
        },
        "model": {
            "provider_class": proposal.provider_class,
            "model_id": proposal.model_id,
            "model_digest": proposal.model_digest,
            "calibration_status": proposal.calibration_status,
        },
    }


def _text_of(candidates: list[dict[str, Any]], candidate_id: Any) -> str | None:
    """Map a provider's candidate_id onto the text the judgment reasons about."""
    return next(
        (c.get("text") for c in candidates if c.get("candidate_id") == candidate_id),
        None,
    )


def _already_stored(store: MemoryStore, entity: str, content: str | None) -> bool:
    if content is None:
        return True
    return any(record.content == content for record in store.find(entity, promoted_only=True))


def _acquire(store: MemoryStore, registry: SourceRegistry, spec: dict[str, Any], receipt: dict[str, Any]) -> int:
    """Pull cited receipts into memory as candidates, then verify before any promotion."""
    receipt["attempted"] = True
    calls = 0
    for source_ref in spec.get("source_refs") or []:
        calls += 1
        source_record = registry.lookup(source_ref)
        if source_record is None:
            receipt["refused"].append({"source_ref": source_ref, "reason": "unknown_source_ref"})
            continue
        record = store.append(
            entity=source_record.entity,
            content=source_record.content,
            source=spec.get("source", "local-source-fixture"),
            source_ref=source_ref,
        )
        receipt["written"].append(record.memory_id)
        _verify_then_promote(store, registry, record, receipt)
    return calls


def _writeback(store: MemoryStore, entity: str, content: str, parent_ids: list[str], receipt: dict[str, Any]) -> int:
    """Store an authorised conclusion with lineage to the evidence that justified it."""
    receipt["attempted"] = True
    parents = [record for record in (store.get(memory_id) for memory_id in parent_ids) if record is not None]
    record = store.append(
        entity=entity,
        content=content,
        source="verified-judgment-writeback",
        source_ref=f"lineage:{sha256_json(sorted(parent_ids))[:16]}",
        related_ids=parent_ids,
    )
    receipt["written"].append(record.memory_id)
    result = verify_derived(record, parents)
    store.set_verification(record.memory_id, status=result.status, detail=result.detail)
    if result.status != "pass":
        receipt["refused"].append({"memory_id": record.memory_id, "reason": result.detail})
        return 1
    try:
        store.promote(record.memory_id)
        receipt["promoted"].append(record.memory_id)
    except PromotionUnauthorized as exc:
        receipt["refused"].append({"memory_id": record.memory_id, "reason": str(exc)})
    return 1


def _verify_then_promote(store: MemoryStore, registry: SourceRegistry, record: Any, receipt: dict[str, Any]) -> None:
    result = verify_record(record, registry)
    store.set_verification(record.memory_id, status=result.status, detail=result.detail)
    refreshed = store.get(record.memory_id)
    if refreshed is None:
        return
    if result.status != "pass":
        receipt["refused"].append({"memory_id": record.memory_id, "reason": result.detail})
        return
    try:
        store.promote(refreshed.memory_id)
        receipt["promoted"].append(refreshed.memory_id)
    except PromotionUnauthorized as exc:
        receipt["refused"].append({"memory_id": refreshed.memory_id, "reason": str(exc)})
