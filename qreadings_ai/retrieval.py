"""Provenance-aware evidence retrieval for QREADINGS.

Retrieval is deliberately lightweight: SQLite token matching ranks stored
source passages and preserves provenance so the model can distinguish primary
text, methodological rules, hypotheses, and secondary evidence.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any


TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class EvidenceRetriever:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        source_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        tokens = [t.lower() for t in TOKEN_RE.findall(query) if len(t) > 1]
        if not tokens:
            return []

        rows = self.connection.execute(
            "SELECT id, source_path, section, evidence_type, content, metadata_json "
            "FROM evidence_passages"
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            if source_types and row["evidence_type"] not in source_types:
                continue
            metadata = json.loads(row["metadata_json"] or "{}")
            haystack = f"{row['section']} {row['content']}".lower()
            hits = sum(1 for token in tokens if token in haystack)
            if hits == 0:
                continue
            score = hits / len(tokens)
            results.append(
                {
                    "id": row["id"],
                    "source_path": row["source_path"],
                    "section": row["section"],
                    "evidence_type": row["evidence_type"],
                    "content": row["content"],
                    "metadata": metadata,
                    "score": round(score, 4),
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]
