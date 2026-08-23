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
REFERENCE_RE = re.compile(r"\b(\d{1,3}):(\d{1,3}(?:[–-]\d{1,3})?)\b")
DAY_RE = re.compile(r"\bqreading\s+day\s+(\d+)\b", re.IGNORECASE)


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

        references = self._reference_queries(query)
        days = self._day_queries(query)
        results: list[dict[str, Any]] = []
        for row in rows:
            if source_types and row["evidence_type"] not in source_types:
                continue
            metadata = self._parse_metadata(row["metadata_json"])
            haystack = " ".join(
                [
                    str(row["section"]),
                    str(row["content"]),
                    str(row["source_path"]),
                    json.dumps(metadata, ensure_ascii=False),
                ]
            ).lower()
            hits = sum(1 for token in tokens if token in haystack)
            if hits == 0:
                continue

            score = hits / len(tokens)
            if any(ref.lower() in haystack for ref in references):
                score += 0.5
            if any(day.lower() in haystack for day in days):
                score += 0.35

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

    @staticmethod
    def _parse_metadata(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _reference_queries(query: str) -> list[str]:
        return [match.group(0).replace("-", "–") for match in REFERENCE_RE.finditer(query)]

    @staticmethod
    def _day_queries(query: str) -> list[str]:
        return [f"qreading day {match.group(1)}" for match in DAY_RE.finditer(query)]
