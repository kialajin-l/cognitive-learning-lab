"""Query-related retrieval over memory records.

The archived experiment runners kept this logic inline; the audit found no
importable retriever, so this is new code rather than an extraction. Matching is
deterministic: exact entity first, then token overlap, and ties break on
``memory_id`` so two runs cannot disagree about what was retrieved.
"""

from __future__ import annotations

import re
from typing import Any

from . import RETRIEVER_VERSION
from .memory.store import MemoryRecord, MemoryStore

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(value: str) -> set[str]:
    return {token for token in _TOKEN.findall(value.lower()) if len(token) > 1}


class RetrievalResult:
    def __init__(self, query: str, matched: list[MemoryRecord], strategy: str) -> None:
        self.query = query
        self.matched = matched
        self.strategy = strategy

    @property
    def matched_ids(self) -> list[str]:
        return [record.memory_id for record in self.matched]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "retriever": RETRIEVER_VERSION,
            "strategy": self.strategy,
            "matched_ids": self.matched_ids,
            "matched": [record.as_dict() for record in self.matched],
        }


def retrieve(store: MemoryStore, *, entity: str, query: str = "", limit: int = 8) -> RetrievalResult:
    exact = store.find(entity)
    if exact:
        return RetrievalResult(query, exact[:limit], "exact_entity")

    query_tokens = tokenize(f"{entity} {query}")
    scored: list[tuple[int, str]] = []
    for memory_id in store.ids():
        record = store.get(memory_id)
        if record is None:
            continue
        overlap = len(query_tokens & (tokenize(record.entity) | tokenize(record.content)))
        if overlap:
            scored.append((-overlap, record.memory_id))
    scored.sort()
    return RetrievalResult(query, [store.get(memory_id) for _, memory_id in scored[:limit]], "token_overlap")
