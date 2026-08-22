"""Lightweight structured memory and retrieval for QREADINGS.

The first implementation deliberately uses SQLite only. Retrieval combines
lexical matching with explicit graph relations so the system does not need a
large vector database to maintain useful state.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from .state import Evidence, Hypothesis


class Memory:
    def __init__(self, path: str | Path = "qreadings_ai.db") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialise()

    def _initialise(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                input_text TEXT NOT NULL,
                state_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                strength REAL NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hypotheses (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                claim TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object_id TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                payload_json TEXT NOT NULL,
                UNIQUE(subject_id, predicate, object_id)
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_investigation
                ON evidence(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_hypotheses_investigation
                ON hypotheses(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_relations_subject
                ON relations(subject_id);
            CREATE INDEX IF NOT EXISTS idx_relations_object
                ON relations(object_id);
            CREATE INDEX IF NOT EXISTS idx_concepts_name
                ON concepts(name);
            """
        )
        self.connection.commit()

    def save_state(self, investigation_id: str, input_text: str, state: dict[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO investigations(id, input_text, state_json)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                input_text=excluded.input_text,
                state_json=excluded.state_json
            """,
            (investigation_id, input_text, json.dumps(state, ensure_ascii=False)),
        )
        self.connection.commit()

    def upsert_concept(
        self,
        name: str,
        description: str = "",
        confidence: float = 0.5,
        *,
        payload: dict[str, Any] | None = None,
    ) -> str:
        existing = self.connection.execute(
            "SELECT id FROM concepts WHERE name = ?", (name,)
        ).fetchone()
        concept_id = existing["id"] if existing else str(uuid4())
        self.connection.execute(
            """
            INSERT INTO concepts(id, name, description, confidence, payload_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                description=excluded.description,
                confidence=excluded.confidence,
                payload_json=excluded.payload_json
            """,
            (
                concept_id,
                name,
                description,
                max(0.0, min(1.0, confidence)),
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        self.connection.commit()
        return concept_id

    def add_relation(
        self,
        subject_id: str,
        predicate: str,
        object_id: str,
        *,
        weight: float = 1.0,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO relations(id, subject_id, predicate, object_id, weight, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(subject_id, predicate, object_id) DO UPDATE SET
                weight=excluded.weight,
                payload_json=excluded.payload_json
            """,
            (
                str(uuid4()),
                subject_id,
                predicate,
                object_id,
                max(0.0, weight),
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def add_evidence(self, investigation_id: str, evidence: Evidence) -> None:
        self.connection.execute(
            """
            INSERT INTO evidence(id, investigation_id, source, content, strength, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source=excluded.source,
                content=excluded.content,
                strength=excluded.strength,
                payload_json=excluded.payload_json
            """,
            (
                evidence.id,
                investigation_id,
                evidence.source,
                evidence.content,
                max(0.0, min(1.0, evidence.strength)),
                json.dumps(asdict(evidence), ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def add_hypothesis(self, investigation_id: str, hypothesis: Hypothesis) -> None:
        self.connection.execute(
            """
            INSERT INTO hypotheses(id, investigation_id, claim, confidence, status, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claim=excluded.claim,
                confidence=excluded.confidence,
                status=excluded.status,
                payload_json=excluded.payload_json
            """,
            (
                hypothesis.id,
                investigation_id,
                hypothesis.claim,
                max(0.0, min(1.0, hypothesis.confidence)),
                hypothesis.status,
                json.dumps(asdict(hypothesis), ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def search_concepts(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Cheap lexical retrieval using SQLite FTS-like LIKE matching.

        This intentionally avoids embeddings at this stage. A later adapter can
        add vector retrieval without changing callers.
        """
        tokens = [token.strip().lower() for token in query.split() if token.strip()]
        if not tokens:
            return []
        clauses = ["lower(name) LIKE ? OR lower(description) LIKE ?"] * len(tokens)
        params: list[str] = []
        for token in tokens:
            pattern = f"%{token}%"
            params.extend((pattern, pattern))
        sql = (
            "SELECT id, name, description, confidence, payload_json "
            "FROM concepts WHERE " + " OR ".join(clauses) + " "
            "ORDER BY confidence DESC LIMIT ?"
        )
        rows = self.connection.execute(sql, [*params, limit]).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "confidence": row["confidence"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def related_concepts(self, concept_id: str, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT r.subject_id, r.predicate, r.object_id, r.weight,
                   s.name AS subject_name, o.name AS object_name
            FROM relations r
            LEFT JOIN concepts s ON s.id = r.subject_id
            LEFT JOIN concepts o ON o.id = r.object_id
            WHERE r.subject_id = ? OR r.object_id = ?
            ORDER BY r.weight DESC LIMIT ?
            """,
            (concept_id, concept_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def retrieve_context(self, query: str, *, concept_limit: int = 6) -> dict[str, Any]:
        concepts = self.search_concepts(query, limit=concept_limit)
        relations: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for concept in concepts:
            for relation in self.related_concepts(concept["id"]):
                key = (
                    relation["subject_id"],
                    relation["predicate"],
                    relation["object_id"],
                )
                if key not in seen:
                    seen.add(key)
                    relations.append(relation)
        return {"concepts": concepts, "relations": relations}

    def close(self) -> None:
        self.connection.close()
