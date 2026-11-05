"""Persistent local memory with separated trust layers.

Every record carries schema version, namespace, content hash, source, capture
time, verification type/version, promotion state and related ids. Model output
and verified facts never share a column: writes always land as
``candidate/unverified`` and only ``verify`` plus ``promote`` can make a record
trusted, so an unverified proposal cannot become memory by asking nicely.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .. import RETRIEVER_VERSION, SCHEMA_VERSION, VERIFICATION_TYPE, VERIFICATION_VERSION
from ..hashing import sha256_text

CALLER_TRUST_FIELDS = frozenset({"verification_status", "promotion_state", "verified", "trusted"})


class PromotionUnauthorized(RuntimeError):
    """A promotion was requested without a passing verification."""


class StoreNotSpecified(RuntimeError):
    """Refusing to mutate a store the caller did not explicitly name."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id           TEXT PRIMARY KEY,
    schema_version      TEXT NOT NULL,
    namespace           TEXT NOT NULL,
    entity              TEXT NOT NULL,
    content             TEXT NOT NULL,
    content_sha256      TEXT NOT NULL,
    source              TEXT NOT NULL,
    source_ref          TEXT NOT NULL,
    captured_at         TEXT NOT NULL,
    verification_type   TEXT NOT NULL,
    verification_version TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    verification_detail TEXT,
    promoted_at         TEXT,
    promotion_state     TEXT NOT NULL,
    related_ids         TEXT NOT NULL,
    retriever_version   TEXT NOT NULL,
    record_json         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS memories_entity ON memories(namespace, entity, promotion_state);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    entity: str
    content: str
    content_sha256: str
    source: str
    source_ref: str
    verification_status: str
    promotion_state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "entity": self.entity,
            "content": self.content,
            "content_sha256": self.content_sha256,
            "source": self.source,
            "source_ref": self.source_ref,
            "verification_status": self.verification_status,
            "promotion_state": self.promotion_state,
        }


class MemoryStore:
    def __init__(self, path: str | Path, *, namespace: str = "default") -> None:
        self.path = Path(path).expanduser().resolve()
        self.namespace = namespace
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def append(
        self,
        *,
        entity: str,
        content: str,
        source: str,
        source_ref: str,
        memory_id: str | None = None,
        related_ids: Iterable[str] = (),
    ) -> MemoryRecord:
        """Write a candidate. Caller-supplied trust fields are dropped, not honoured."""
        record_id = memory_id or f"{self.namespace}:{entity}:{sha256_text(content)[:16]}"
        payload = {
            "memory_id": record_id,
            "schema_version": SCHEMA_VERSION,
            "namespace": self.namespace,
            "entity": entity,
            "content": content,
            "content_sha256": sha256_text(content),
            "source": source,
            "source_ref": source_ref,
            "captured_at": _now(),
            "verification_type": VERIFICATION_TYPE,
            "verification_version": VERIFICATION_VERSION,
            "verification_status": "unverified",
            "promotion_state": "candidate",
            "related_ids": sorted(related_ids),
            "retriever_version": RETRIEVER_VERSION,
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories (memory_id, schema_version, namespace, entity, content,
                    content_sha256, source, source_ref, captured_at, verification_type,
                    verification_version, verification_status, verification_detail, promoted_at,
                    promotion_state, related_ids, retriever_version, record_json)
                VALUES (:memory_id, :schema_version, :namespace, :entity, :content,
                    :content_sha256, :source, :source_ref, :captured_at, :verification_type,
                    :verification_version, :verification_status, NULL, NULL,
                    :promotion_state, :related_ids, :retriever_version, :record_json)
                ON CONFLICT(memory_id) DO UPDATE SET
                    content = excluded.content,
                    content_sha256 = excluded.content_sha256,
                    captured_at = excluded.captured_at,
                    verification_status = 'unverified',
                    promotion_state = 'candidate',
                    promoted_at = NULL,
                    record_json = excluded.record_json
                """,
                {
                    **payload,
                    "related_ids": json.dumps(payload["related_ids"]),
                    "record_json": json.dumps(payload, ensure_ascii=False),
                },
            )
        return self.get(record_id)

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        return _record(row) if row else None

    def ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT memory_id FROM memories WHERE namespace = ? ORDER BY memory_id", (self.namespace,)
            ).fetchall()
        return [row["memory_id"] for row in rows]

    def find(self, entity: str, *, promoted_only: bool = False) -> list[MemoryRecord]:
        query = "SELECT * FROM memories WHERE namespace = ? AND entity = ?"
        if promoted_only:
            query += " AND promotion_state = 'promoted'"
        query += " ORDER BY memory_id"
        with self._connect() as connection:
            rows = connection.execute(query, (self.namespace, entity)).fetchall()
        return [_record(row) for row in rows]

    def set_verification(self, memory_id: str, *, status: str, detail: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE memories SET verification_status = ?, verification_detail = ? WHERE memory_id = ?",
                (status, detail, memory_id),
            )

    def promote(self, memory_id: str) -> MemoryRecord:
        """Promote only a record whose verification passed and whose hash still matches."""
        record = self.get(memory_id)
        if record is None:
            raise PromotionUnauthorized(f"unknown memory_id {memory_id}")
        if record.verification_status != "pass":
            raise PromotionUnauthorized(f"verification_status={record.verification_status!r}")
        if record.content_sha256 != sha256_text(record.content):
            self.set_verification(memory_id, status="tampered", detail="content hash mismatch at promote")
            raise PromotionUnauthorized("content hash mismatch at promote")
        with self._connect() as connection:
            connection.execute(
                "UPDATE memories SET promotion_state = 'promoted', promoted_at = ?, record_json = ? WHERE memory_id = ?",
                (_now(), json.dumps({**self._raw(memory_id), "promotion_state": "promoted"}, ensure_ascii=False), memory_id),
            )
        return self.get(memory_id)

    def _raw(self, memory_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT record_json FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        return json.loads(row["record_json"])

    def integrity_check(self) -> dict[str, Any]:
        """Recompute every stored hash; tampered records lose trust."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT memory_id, content, content_sha256 FROM memories WHERE namespace = ?",
                (self.namespace,),
            ).fetchall()
            tampered = [row["memory_id"] for row in rows if sha256_text(row["content"]) != row["content_sha256"]]
            connection.executemany(
                "UPDATE memories SET verification_status = 'tampered', promotion_state = 'quarantined' WHERE memory_id = ?",
                [(memory_id,) for memory_id in tampered],
            )
            connection.commit()
        return {
            "checked": len(rows),
            "quarantined": len(tampered),
            "tampered": sorted(tampered),
            "store": str(self.path),
        }

    def stats(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT promotion_state, verification_status, COUNT(*) AS total FROM memories WHERE namespace = ? GROUP BY 1, 2",
                (self.namespace,),
            ).fetchall()
        return {
            "store": str(self.path),
            "namespace": self.namespace,
            "records": [dict(row) for row in rows],
            "total": sum(row["total"] for row in rows),
        }

    def clear(self, *, confirm_path: str | Path) -> int:
        """Delete rows only when the caller names this exact store again."""
        target = Path(confirm_path).expanduser().resolve()
        if target != self.path:
            raise StoreNotSpecified(f"confirmed path {target} does not match store {self.path}")
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE namespace = ?", (self.namespace,))
        return cursor.rowcount


def _record(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        memory_id=row["memory_id"],
        entity=row["entity"],
        content=row["content"],
        content_sha256=row["content_sha256"],
        source=row["source"],
        source_ref=row["source_ref"],
        verification_status=row["verification_status"],
        promotion_state=row["promotion_state"],
    )
