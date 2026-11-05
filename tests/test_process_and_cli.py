"""Independent-process reuse and CLI behaviour, exercised through real subprocesses."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import request_for

from cognitive_runtime.config import DEFAULT_DIR
from cognitive_runtime.memory.store import MemoryStore
from cognitive_runtime.pipeline import run_request

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# This interpreter runs in isolated mode and ignores PYTHONPATH, so the child
# process is bootstrapped through sys.path instead.
_BOOTSTRAP = (
    "import sys; sys.path.insert(0, %r); "
    "from cognitive_runtime.cli import main; raise SystemExit(main())" % str(PACKAGE_ROOT / "src")
)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", _BOOTSTRAP, *args], capture_output=True, text=True, timeout=180)


def test_second_process_reads_the_same_memory(config):
    first = run_request(request_for(acquire=["dir-001"]), config)
    assert first["status"] == "answered"
    evidence_ids = sorted(first["evidence_refs"])
    assert evidence_ids, "the writing process must have persisted something"

    request_path = Path(config.store_path).parent / "reuse.json"
    request_path.write_text(json.dumps(request_for()), encoding="utf-8")
    completed = _run(
        [
            "--config",
            str(DEFAULT_DIR / "config.json"),
            "infer",
            "--input",
            str(request_path),
            "--store",
            str(config.store_path),
            "--namespace",
            "test",
        ]
    )
    assert completed.returncode == 0, completed.stderr

    result = json.loads(completed.stdout)
    assert result["status"] == "answered", "a fresh process must reuse the persisted memory, not start cold"
    assert result["cost"]["model_calls"] == 1
    assert result["schema_version"] == "cognitive-runtime/decision-output/v1"

    store = MemoryStore(config.resolve_store_path(), namespace="test")
    assert sorted(record.memory_id for record in store.find("widget-alpha", promoted_only=True)) == evidence_ids


def test_packaged_example_runs_out_of_the_box(tmp_path):
    """The documented install command has to work against the shipped example, not a repo fixture."""
    store = tmp_path / "out-of-the-box.sqlite"
    completed = _run(["infer", "--input", str(DEFAULT_DIR / "examples" / "request.json"), "--store", str(store)])
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "answered"
    assert result["final_answer"] == "team-north"
    assert result["authorization"] == "verified_judgment"

    rerun = _run(["infer", "--input", str(DEFAULT_DIR / "examples" / "request.json"), "--store", str(store)])
    assert json.loads(rerun.stdout)["memory_hit"] is True, "the second process reuses the persisted memory"


def test_conflicting_example_abstains(tmp_path):
    store = tmp_path / "conflict.sqlite"
    completed = _run(["infer", "--input", str(DEFAULT_DIR / "examples" / "request-conflict.json"), "--store", str(store)])
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "abstained"
    assert result["judgment"]["reason"] == "conflicting_verified_rules"


def test_doctor_reports_mock_readiness(config):
    completed = _run(["--config", str(DEFAULT_DIR / "config.json"), "doctor", "--store", str(config.store_path)])
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["provider"] == "mock"
    assert report["python"]["meets_minimum"] is True
    assert report["model"]["status"] == "not_required"


def test_doctor_names_the_model_blocker_without_downloading():
    config_path = DEFAULT_DIR / "laya-offline.json"
    completed = _run(["--config", str(config_path), "doctor"])
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["provider"] == "laya"
    assert "model_unavailable_or_unverified" in report["blockers"] or report["model"].get("status") == "unavailable"


def test_seeded_records_reach_memory_only_through_verify(tmp_path):
    """A hand-written record is a candidate until the receipt registry says otherwise."""
    store = tmp_path / "seeded.sqlite"
    seeded = _run(["memory", "seed", "--store", str(store), "--input", str(DEFAULT_DIR / "examples" / "seed-records.jsonl")])
    assert seeded.returncode == 0, seeded.stderr
    payload = json.loads(seeded.stdout)
    assert len(payload["written"]) == 2
    assert payload["note"] == "seeded records are candidates and unverified"

    verified = _run(["memory", "verify", "--store", str(store)])
    assert verified.returncode == 0, verified.stderr
    outcomes = {entry["memory_id"]: entry for entry in json.loads(verified.stdout)["outcomes"]}
    states = {entry["status"]: entry["promoted"] for entry in outcomes.values()}
    assert states["pass"] is True
    assert states["fail"] is False

    request = {
        "run_id": "seeded-replay",
        "question": "Which team is widget-beta assigned to?",
        "entity": "widget-beta",
        "candidates": [{"candidate_id": "c1", "text": "team-north"}, {"candidate_id": "c2", "text": "team-south"}],
    }
    request_path = tmp_path / "seeded-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    answered = _run(["infer", "--input", str(request_path), "--store", str(store)])
    assert answered.returncode == 0, answered.stderr
    result = json.loads(answered.stdout)
    assert result["status"] == "answered"
    assert result["final_answer"] == "team-south"
    assert result["cost"]["acquisition_calls"] == 0, "the answer came from memory, not from re-acquiring"


def test_memory_inspect_and_clear_require_an_explicit_store(config):
    run_request(request_for(acquire=["dir-001"]), config)

    completed = _run(["memory", "inspect", "--store", str(config.store_path), "--namespace", "test"])
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["records"]

    refused = _run(["memory", "clear", "--store", str(config.store_path), "--namespace", "test"])
    assert refused.returncode == 2
    assert "requires --yes" in json.loads(refused.stdout)["detail"]

    cleared = _run(["memory", "clear", "--store", str(config.store_path), "--namespace", "test", "--yes"])
    assert cleared.returncode == 0
    assert json.loads(cleared.stdout)["records_removed"] >= 1


def test_worker_is_imported_as_a_module_not_run_as_a_script():
    # Script mode would put cognitive_runtime/model/ at the child's
    # sys.path[0], where this package's own `laya.py` shadows the third-party
    # `laya` package and the child dies on its relative imports. Regression
    # for the defect the real-model smoke exposed on a normal (venv) install.
    from cognitive_runtime.model.laya import LayaProvider

    command = LayaProvider()._worker_command()
    assert command[1] == "-c"
    assert "from cognitive_runtime.model.laya_worker import main" in command[2]
    assert not command[2].startswith(sys.executable)
    # the bootstrapped path is the package root, so the child imports the real
    # third-party `laya` from its own site-packages, not our sibling module
    assert command[2].split("sys.path.insert(0, ")[1].startswith("'")
