"""Formal proposal path: pinned upstream checkpoint, integrity-checked, subprocess-isolated.

Three deliberate properties:

* ``laya.load`` cannot accept a revision in 0.3.20, so the snapshot is resolved
  first and the ``snapshots/<sha>`` directory is what gets loaded. Identity is
  always ``laya:<repo>@<sha>``; an unpinned load is reported, not hidden.
* The local Hugging Face cache in the audit environment is not in standard LFS
  layout, so "present in cache" proves nothing. The weights are hashed and
  compared against the pinned digest before the model is trusted.
* Inference runs in a child process with a wall-clock budget, so a hung load
  cannot outlive the call.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..hashing import sha256_file
from ..prompting import QUESTION_ID
from .base import Proposal

REPO_ID = "convaiinnovations/laya"
PINNED_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
ALLOW_PATTERNS = ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")
PINNED_FILE_SHA256 = {
    "model.safetensors": "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c",
}
# The snapshot ships encoder/config.json only; the encoder weights are a second
# upstream download. Recorded here so doctor can say what is missing.
ENCODER_REPO_ID = "answerdotai/ModernBERT-large"
MAX_CANDIDATES = 20


class ModelIntegrityError(RuntimeError):
    """Weights on disk do not match the pinned digest."""


class ModelUnavailable(RuntimeError):
    """The checkpoint could not be resolved locally or from the hub."""


@dataclass
class LayaSettings:
    repo_id: str = REPO_ID
    revision: str = PINNED_REVISION
    local_dir: str | None = None
    device: str = "cpu"
    timeout_seconds: int = 600
    allow_download: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "LayaSettings":
        model = config.get("model") or {}
        return cls(
            repo_id=model.get("repo_id", REPO_ID),
            revision=model.get("revision", PINNED_REVISION),
            local_dir=model.get("local_dir"),
            device=model.get("device", "cpu"),
            timeout_seconds=int(model.get("timeout_seconds", 600)),
            allow_download=bool(model.get("allow_download", True)),
        )


class LayaProvider:
    provider_class = "real"

    def __init__(self, settings: LayaSettings | None = None) -> None:
        self.settings = settings or LayaSettings()
        self.model_id = "laya:root"
        self._resolved: tuple[str, str] | None = None
        self.identity_warning: str | None = None

    @property
    def model_digest(self) -> str:
        if self._resolved is None:
            return f"laya:{self.settings.repo_id}@not-resolved"
        return f"laya:{self.settings.repo_id}@{self._resolved[0]}"

    def resolve(self) -> tuple[str, str]:
        """Return (revision sha, snapshot directory) without trusting either yet."""
        if self._resolved is not None:
            return self._resolved
        if self.settings.local_dir:
            root = Path(self.settings.local_dir).expanduser().resolve()
            if not root.exists():
                raise ModelUnavailable(f"configured model local_dir does not exist: {root}")
            revision = self.settings.revision if len(self.settings.revision) == 40 else "unpinned-local-copy"
            if len(self.settings.revision) != 40:
                self.identity_warning = "local_dir used without a 40-character pinned revision"
            self._resolved = (revision, str(root))
            return self._resolved
        if not self.settings.allow_download:
            raise ModelUnavailable("allow_download is false and no local_dir is configured")
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:  # pragma: no cover - dependency presence is environmental
            raise ModelUnavailable(f"huggingface_hub is not installed: {exc}") from exc
        try:
            path = snapshot_download(
                self.settings.repo_id,
                revision=self.settings.revision,
                allow_patterns=list(ALLOW_PATTERNS),
            )
        except Exception as exc:  # network, auth or hub errors are all "unavailable"
            raise ModelUnavailable(f"snapshot_download failed for {self.settings.repo_id}@{self.settings.revision}: {exc}") from exc
        resolved_sha = Path(path).name
        if self.settings.revision and resolved_sha != self.settings.revision:
            self.identity_warning = f"resolved {resolved_sha} differs from requested {self.settings.revision}"
        self._resolved = (resolved_sha, path)
        return self._resolved

    def verify_integrity(self) -> dict[str, Any]:
        """Hash the pinned files; refuse to proceed on mismatch."""
        _, snapshot = self.resolve()
        report: dict[str, Any] = {"snapshot": snapshot, "checked": {}, "status": "pass"}
        for name, expected in PINNED_FILE_SHA256.items():
            target = Path(snapshot) / name
            if not target.exists():
                report["checked"][name] = {"status": "missing", "expected_sha256": expected}
                report["status"] = "fail"
                continue
            actual = sha256_file(target)
            report["checked"][name] = {
                "status": "pass" if actual == expected else "mismatch",
                "expected_sha256": expected,
                "actual_sha256": actual,
                "byte_size": target.stat().st_size,
            }
            if actual != expected:
                report["status"] = "fail"
        if report["status"] != "pass":
            raise ModelIntegrityError(json.dumps(report, ensure_ascii=False))
        return report

    def propose(self, *, state: str, questions: dict[str, dict[str, Any]]) -> Proposal:
        payload_question = questions.get(QUESTION_ID) or {}
        criteria = payload_question.get("criteria") or {}
        if len(criteria) > MAX_CANDIDATES:
            return self._error("schema_failure", f"{len(criteria)} candidates exceed the option budget {MAX_CANDIDATES}")
        try:
            self.verify_integrity()
        except ModelIntegrityError as exc:
            return self._error("runtime_error", f"model integrity check failed: {exc}")
        except ModelUnavailable as exc:
            return self._error("runtime_error", f"model unavailable: {exc}")

        payload = {
            "snapshot": self._resolved[1],
            "device": self.settings.device,
            "state": state,
            "questions": questions,
        }
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                self._worker_command(),
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.settings.timeout_seconds,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired:
            return self._error("timeout", f"model worker exceeded {self.settings.timeout_seconds}s", started)
        except OSError as exc:
            return self._error("runtime_error", f"worker launch failed: {exc}", started)

        latency = round((time.perf_counter() - started) * 1000)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return self._error(
                "runtime_error",
                f"worker exited {completed.returncode} without JSON; stderr_sha256={_hash(completed.stderr)}",
                started,
            )
        result["latency_ms"] = latency
        return proposal_from_worker(result, model_id=self.model_id, model_digest=self.model_digest)

    def _worker_command(self) -> list[str]:
        # The worker must be imported as a package submodule, not run as a
        # script file: script mode puts this directory at sys.path[0], where
        # this file's own name (`laya.py`) shadows the third-party `laya`
        # package and crashes the child with a relative-import error.
        root = str(Path(__file__).resolve().parents[2])
        bootstrap = (
            "import sys; sys.path.insert(0, %r); "
            "from cognitive_runtime.model.laya_worker import main; main()" % (root,)
        )
        return [sys.executable, "-c", bootstrap]

    def _error(self, code: str, message: str, started: float | None = None) -> Proposal:
        return Proposal(
            status=code,
            provider_class=self.provider_class,
            model_id=self.model_id,
            model_digest=self.model_digest,
            calibration_status="unknown",
            latency_ms=round((time.perf_counter() - started) * 1000) if started else None,
            error={"code": code, "message": message},
        )

    def identity(self) -> dict[str, Any]:
        return {
            "provider_class": self.provider_class,
            "model_id": self.model_id,
            "model_digest": self.model_digest,
            "repo_id": self.settings.repo_id,
            "requested_revision": self.settings.revision,
            "resolved_revision": self._resolved[0] if self._resolved else None,
            "snapshot": self._resolved[1] if self._resolved else None,
            "device": self.settings.device,
            "identity_warning": self.identity_warning,
            "encoder_dependency": ENCODER_REPO_ID,
        }


def _hash(value: str | None) -> str:
    import hashlib

    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def proposal_from_worker(result: dict[str, Any], *, model_id: str, model_digest: str) -> Proposal:
    """Map the worker payload onto the typed proposal, fail-closed."""
    status = result.get("status", "runtime_error")
    usage = result.get("usage") or {}
    base = {
        "model_id": model_id,
        "model_digest": model_digest,
        "provider_class": "real",
        "calibration_status": result.get("calibration_status", "unknown"),
        "latency_ms": result.get("latency_ms"),
        "prompt_tokens": usage.get("input_tokens"),
        "completion_tokens": usage.get("output_tokens"),
        "retries": result.get("retries", 0),
    }
    if status != "ok":
        return Proposal(
            status=status if status in ("abstain", "schema_failure", "timeout", "runtime_error") else "runtime_error",
            error={"code": status, "message": result.get("message", "worker reported failure")},
            **base,
        )
    selected = result.get("selected")
    probabilities = result.get("probabilities") or {}
    if not isinstance(selected, str) or not isinstance(probabilities, dict):
        return Proposal(status="schema_failure", error={"code": "schema_failure", "message": "worker payload malformed"}, **base)
    return Proposal(status="ok", selected=selected, probabilities=probabilities, confidence=result.get("confidence"), **base)
