"""Positive chain: acquire -> verify -> promote -> judge -> answer -> writeback -> reuse."""

from __future__ import annotations

from conftest import request_for

from cognitive_runtime.memory.store import MemoryStore
from cognitive_runtime.pipeline import run_request
from cognitive_runtime.sources import expected_content


def test_cold_start_without_evidence_abstains(config):
    result = run_request(request_for(), config)
    assert result["status"] == "abstained"
    assert result["authorization"] == "none"
    assert result["abstain_reason"] == "no_verified_matching_rule"
    assert result["writeback"]["allowed"] is False
    assert result["memory_hit"] is False


def test_acquisition_makes_a_verified_answer_possible(config):
    result = run_request(request_for(acquire=["dir-001"]), config)
    assert result["status"] == "answered"
    assert result["final_answer"] == "team-north"
    assert result["selected"] == "c1"
    assert result["authorization"] == "verified_judgment"
    assert result["memory_hit"] is True
    assert result["cost"]["model_calls"] == 1
    assert result["model"]["provider_class"] == "mock"


def test_second_run_reuses_persisted_memory_without_reacquiring(config):
    first = run_request(request_for(acquire=["dir-001"]), config)
    assert first["status"] == "answered"

    second = run_request(request_for(), config)
    assert second["status"] == "answered"
    assert second["memory_hit"] is True
    assert second["cost"]["acquisition_calls"] == 0
    assert second["evidence_refs"] == first["evidence_refs"]


def test_writeback_of_authorised_conclusion_is_recorded(config):
    result = run_request(request_for("widget-beta", acquire=["dir-002"]), config)
    assert result["status"] == "answered"
    assert result["writeback"]["allowed"] is True
    store = MemoryStore(config.resolve_store_path(), namespace="test")
    promoted = [record for record in store.find("widget-beta") if record.promotion_state == "promoted"]
    assert expected_content("widget-beta", "team-south") in [record.content for record in promoted]


def test_unknown_source_ref_is_refused_not_stored(config):
    result = run_request(request_for(acquire=["dir-999"]), config)
    assert result["status"] == "abstained"
    assert result["writeback_receipt"]["refused"] == [{"source_ref": "dir-999", "reason": "unknown_source_ref"}]
    assert result["writeback_receipt"]["promoted"] == []


def test_proposal_and_judgment_agreement_is_reported_in_text_terms(config):
    result = run_request(request_for(acquire=["dir-001"]), config)
    assert result["raw_proposal"]["selected"] == "c1"
    assert result["final_answer"] == "team-north"
    assert result["proposal_agrees_with_judgment"] is True


def test_output_carries_layered_provenance_not_a_single_verdict(config):
    result = run_request(request_for(acquire=["dir-001"]), config)
    for key in ("raw_proposal", "judgment", "verification", "writeback", "writeback_receipt", "authorization"):
        assert key in result
    assert result["raw_proposal"]["provider_class"] == "mock"
    assert result["verification"]["scope"] == "provenance consistency, not external truth"
    assert result["cost"]["monetary_cost"] is None
