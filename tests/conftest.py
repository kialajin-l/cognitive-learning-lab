from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cognitive_runtime.config import RuntimeConfig  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def write_sources(path: Path, rows: list[dict]) -> Path:
    import json

    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def config(tmp_path) -> RuntimeConfig:
    sources = write_sources(
        tmp_path / "sources.jsonl",
        [
            {"ref": "dir-001", "entity": "widget-alpha", "label": "team-north", "captured_at": "2026-11-05T00:00:00+00:00"},
            {"ref": "dir-002", "entity": "widget-beta", "label": "team-south", "captured_at": "2026-11-05T00:00:00+00:00"},
            {"ref": "dir-003", "entity": "widget-alpha", "label": "team-south", "captured_at": "2026-11-05T00:00:00+00:00"},
        ],
    )
    return RuntimeConfig(provider="mock", namespace="test", store_path=str(tmp_path / "memory.sqlite"), sources_path=str(sources))


def request_for(entity: str = "widget-alpha", acquire: list[str] | None = None) -> dict:
    payload = {
        "run_id": "test-run",
        "question": f"Which team is {entity} assigned to?",
        "entity": entity,
        "candidates": [
            {"candidate_id": "c1", "text": "team-north"},
            {"candidate_id": "c2", "text": "team-south"},
        ],
    }
    if acquire is not None:
        payload["acquire"] = {"source_refs": acquire, "source": "local-source-fixture"}
    return payload
