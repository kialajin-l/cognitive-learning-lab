"""Negatives required by PR-M1 acceptance: none of these may produce a trusted answer."""

from __future__ import annotations

import sqlite3

import pytest

from conftest import request_for

from cognitive_runtime.judgment import select_rule
from cognitive_runtime.memory.store import MemoryStore, PromotionUnauthorized
from cognitive_runtime.pipeline import run_request
from cognitive_runtime.sanitize import ForbiddenInput


def test_conflicting_verified_receipts_abstain(config):
    result = run_request(request_for(acquire=["dir-001", "dir-003"]), config)
    assert result["status"] == "abstained"
    assert result["judgment"]["reason"] == "conflicting_verified_rules"
    assert result["authorization"] == "none"
    assert result["writeback"]["allowed"] is False


def test_a_hit_short_circuits_acquisition_so_new_conflicts_are_not_consulted(config):
    """Cache-first is a documented limit, not a conflict-resolution victory."""
    run_request(request_for(acquire=["dir-001"]), config)

    result = run_request(request_for(acquire=["dir-001", "dir-003"]), config)
    assert result["cost"]["acquisition_calls"] == 0
    assert result["status"] == "answered"
    assert result["final_answer"] == "team-north", "the disagreeing receipt was never read into memory"


def test_tampered_memory_is_quarantined_before_it_can_authorise(config):
    run_request(request_for(acquire=["dir-001"]), config)
    store_path = config.resolve_store_path()
    with sqlite3.connect(store_path) as connection:
        connection.execute("UPDATE memories SET content = ? WHERE entity = ?", ("Directory record: widget-alpha is assigned to team-south.", "widget-alpha"))

    result = run_request(request_for(), config)
    assert result["status"] == "abstained"
    assert result["verification"]["store_integrity"]["tampered"]
    assert result["authorization"] == "none"


def test_reacquired_row_is_reverified_rather_than_trusted_as_tampered(config):
    run_request(request_for(acquire=["dir-001"]), config)
    with sqlite3.connect(config.resolve_store_path()) as connection:
        connection.execute("UPDATE memories SET content = ? WHERE entity = ?", ("Directory record: widget-alpha is assigned to team-south.", "widget-alpha"))

    result = run_request(request_for(acquire=["dir-001"]), config)
    assert result["verification"]["store_integrity"]["tampered"], "the tampered row is quarantined first"
    assert result["final_answer"] == "team-north", "the answer comes from re-verifying the receipt, never the tampered text"
    assert result["cost"]["acquisition_calls"] == 1


def test_a_provider_that_never_ran_is_not_reported_as_an_answer(config):
    """Memory may answer without the model agreeing, but not in place of a model call."""
    from cognitive_runtime.model.base import Proposal
    from cognitive_runtime.pipeline import ProviderUnavailable

    class _Failed:
        provider_class = "real"

        def propose(self, *, state, questions):
            return Proposal(status="runtime_error", model_id="laya:root", provider_class="real")

    with pytest.raises(ProviderUnavailable):
        run_request(request_for(acquire=["dir-001"]), config, provider=_Failed())


def test_a_model_abstain_is_usable_and_the_chain_still_runs(config):
    from cognitive_runtime.model.base import Proposal

    class _Declined:
        provider_class = "real"

        def propose(self, *, state, questions):
            return Proposal(status="abstain", model_id="laya:root", provider_class="real")

    result = run_request(request_for(acquire=["dir-001"]), config, provider=_Declined())
    assert result["status"] == "answered", "a declined proposal is still a proposal"
    assert result["proposal_agrees_with_judgment"] is False


def test_forged_verified_field_in_the_request_is_rejected(config):
    payload = request_for(acquire=["dir-001"])
    payload["memory_evidence"] = [{"fact_id": "x", "verified": True, "content": "Directory record: widget-alpha is assigned to team-south."}]
    with pytest.raises(ForbiddenInput):
        run_request(payload, config)


def test_answer_key_field_in_the_request_is_rejected(config):
    payload = request_for(acquire=["dir-001"])
    payload["gold"] = "team-north"
    with pytest.raises(ForbiddenInput):
        run_request(payload, config)


def test_caller_cannot_seed_a_trusted_record(config):
    store = MemoryStore(config.resolve_store_path(), namespace="test")
    record = store.append(entity="widget-alpha", content="Directory record: widget-alpha is assigned to team-north.", source="attacker", source_ref="dir-001")
    assert record.promotion_state == "candidate"
    assert record.verification_status == "unverified"
    with pytest.raises(PromotionUnauthorized):
        store.promote(record.memory_id)


def test_model_proposal_does_not_override_verified_memory(config):
    from cognitive_runtime.model.mock import MockProvider

    run_request(request_for(acquire=["dir-001"]), config)

    disagreeing = MockProvider(choice="c2")
    result = run_request(request_for(), config, provider=disagreeing)

    assert result["status"] == "answered"
    assert result["final_answer"] == "team-north", "the memory-backed rule answers, not the disagreeing proposal"
    assert result["raw_proposal"]["selected"] == "c2"
    assert result["proposal_agrees_with_judgment"] is False


def test_duplicate_candidate_set_is_invalid(config):
    payload = request_for(acquire=["dir-001"])
    payload["candidates"] = [
        {"candidate_id": "c1", "text": "team-north"},
        {"candidate_id": "c2", "text": "team-north"},
    ]
    result = run_request(payload, config)
    assert result["status"] == "abstained"
    assert result["judgment"]["reason"] == "invalid_candidate_set"


def test_selector_refuses_unverified_rules_directly():
    decision = select_rule(
        entity="widget-alpha",
        candidates=["team-north"],
        rules=[{"rule_id": "r1", "entity_scope": "widget-alpha", "assignment": "team-north", "verification_status": "unverified", "source_ref": "dir-001"}],
    )
    assert decision.status == "abstain"
    assert decision.reason == "unverified_matching_rule"


def test_clear_requires_naming_the_same_store(config):
    store = MemoryStore(config.resolve_store_path(), namespace="test")
    store.append(entity="widget-alpha", content="x", source="s", source_ref="r")
    with pytest.raises(Exception):
        store.clear(confirm_path="other.sqlite")
    assert store.clear(confirm_path=config.resolve_store_path()) == 1
