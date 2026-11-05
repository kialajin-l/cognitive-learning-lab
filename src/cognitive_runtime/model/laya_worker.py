"""Child-process inference worker for the real Laya path.

Kept separate so the parent can enforce a wall-clock budget by killing this
process, and so the heavy torch/laya import never loads for mock runs, ``doctor``
or ``--provider mock``.

Reads a JSON payload on stdin, writes one JSON result on stdout. Exit code 0
means a result was produced (it may still be a failure status); a crash writes
nothing, which the parent records as ``runtime_error`` rather than an answer.
"""

from __future__ import annotations

import json
import sys
import warnings
from typing import Any


def run(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = payload["snapshot"]
    device = payload.get("device", "cpu")
    questions = payload["questions"]

    caught: list[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            import laya

            agent = laya.load(snapshot, device=device)
            caught = list(recorded)
            raw = agent.predict(payload["state"], questions)
    except ImportError as exc:
        return {"status": "runtime_error", "message": f"laya package unavailable: {exc}"}
    except Exception as exc:  # any model-side failure must not look like an answer
        return {"status": "runtime_error", "message": f"{type(exc).__name__}: {exc}"}

    warning_texts = [str(item.message) for item in caught]
    calibration_status = "uncalibrated" if any("temperature" in text.lower() for text in warning_texts) else "unknown"

    if not isinstance(raw, dict):
        return {"status": "schema_failure", "message": "predict returned a non-object", "calibration_status": calibration_status}
    answers = raw.get("answers")
    answer = answers.get("sel") if isinstance(answers, dict) else None
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        return {
            "status": "schema_failure",
            "message": "missing answers.sel choice payload",
            "usage": raw.get("usage"),
            "calibration_status": calibration_status,
        }
    selected = answer.get("choice")
    probabilities = answer.get("probabilities")
    if not isinstance(selected, str) or not isinstance(probabilities, dict):
        return {
            "status": "schema_failure",
            "message": "choice/probabilities missing or wrong type",
            "usage": raw.get("usage"),
            "calibration_status": calibration_status,
        }
    return {
        "status": "ok",
        "selected": selected,
        "probabilities": {str(key): float(value) for key, value in probabilities.items()},
        "confidence": answer.get("answer_confidence"),
        "usage": raw.get("usage"),
        "calibration_status": calibration_status,
        "warnings": warning_texts[:10],
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "schema_failure", "message": f"invalid stdin JSON: {exc}"}))
        return 0
    print(json.dumps(run(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
