"""Lightweight structured memory and retrieval for QREADINGS."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from .retrieval import EvidenceRetriever
from .state import Evidence, Hypothesis


REFERENCE_RE = re.compile(r"\b(\d{1,3}):(\d{1,3}(?:[–-]\d{1,3})?)\b")
DAY_RE = re.compile(r"\bqreading\s+day\s+(\d+)\b", re.IGNORECASE)


class Memory:
    def __init__(self, path: str | Path = "qreadings_ai.db") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialise()
        self.retriever = EvidenceRetriever(self.connection)

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

            CREATE TABLE IF NOT EXISTS evidence_passages (
                id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                section TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL
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

            CREATE TABLE IF NOT EXISTS reconstruction_versions (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                day_number INTEGER,
                title TEXT NOT NULL,
                reference TEXT,
                trajectory_key TEXT,
                translation TEXT NOT NULL,
                word_of_day TEXT,
                translation_note TEXT,
                theme TEXT,
                raw_text TEXT NOT NULL,
                source_path TEXT NOT NULL,
                metadata_json TEXT NOT NULL
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
            CREATE INDEX IF NOT EXISTS idx_passages_type
                ON evidence_passages(evidence_type);
            CREATE INDEX IF NOT EXISTS idx_reconstruction_trajectory
                ON reconstruction_versions(trajectory_key);
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
                str(uuid4()), subject_id, predicate, object_id,
                max(0.0, weight), json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def add_evidence(self, investigation_id: str, evidence: Evidence) -> None:
        self.connection.execute(
            """
            INSERT INTO evidence(id, investigation_id, source, content, strength, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source=excluded.source, content=excluded.content,
                strength=excluded.strength, payload_json=excluded.payload_json
            """,
            (
                evidence.id, investigation_id, evidence.source, evidence.content,
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
                claim=excluded.claim, confidence=excluded.confidence,
                status=excluded.status, payload_json=excluded.payload_json
            """,
            (
                hypothesis.id, investigation_id, hypothesis.claim,
                max(0.0, min(1.0, hypothesis.confidence)), hypothesis.status,
                json.dumps(asdict(hypothesis), ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def add_passage(
        self,
        source_path: str,
        section: str,
        content: str,
        *,
        evidence_type: str = "source",
        metadata: dict[str, Any] | None = None,
        passage_id: str | None = None,
    ) -> str:
        passage_id = passage_id or str(uuid4())
        self.connection.execute(
            """
            INSERT INTO evidence_passages(id, source_path, section, evidence_type, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_path=excluded.source_path, section=excluded.section,
                evidence_type=excluded.evidence_type, content=excluded.content,
                metadata_json=excluded.metadata_json
            """,
            (
                passage_id, source_path, section, evidence_type, content,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.connection.commit()
        return passage_id

    def add_reconstruction_version(self, version: Any) -> None:
        """Persist a parsed longitudinal reconstruction without judging it."""
        self.connection.execute(
            """
            INSERT INTO reconstruction_versions(
                entry_id, entry_type, ordinal, day_number, title, reference,
                trajectory_key, translation, word_of_day, translation_note,
                theme, raw_text, source_path, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_id) DO UPDATE SET
                entry_type=excluded.entry_type,
                ordinal=excluded.ordinal,
                day_number=excluded.day_number,
                title=excluded.title,
                reference=excluded.reference,
                trajectory_key=excluded.trajectory_key,
                translation=excluded.translation,
                word_of_day=excluded.word_of_day,
                translation_note=excluded.translation_note,
                theme=excluded.theme,
                raw_text=excluded.raw_text,
                source_path=excluded.source_path,
                metadata_json=excluded.metadata_json
            """,
            (
                version.entry_id, version.entry_type, version.ordinal,
                version.day_number, version.title, version.reference,
                version.trajectory_key, version.translation,
                version.word_of_day, version.translation_note, version.theme,
                version.raw_text, version.source_path,
                json.dumps(version.metadata, ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def reconstruction_trajectory(self, trajectory_key: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM reconstruction_versions
            WHERE trajectory_key = ?
            ORDER BY CASE WHEN day_number IS NULL THEN 999999 ELSE day_number END ASC,
                     ordinal ASC
            """,
            (trajectory_key,),
        ).fetchall()
        return [dict(row) for row in rows]

    def search_reconstructions(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        references = [m.group(0).replace("-", "–") for m in REFERENCE_RE.finditer(query)]
        days = [int(m.group(1)) for m in DAY_RE.finditer(query)]

        if references:
            placeholders = ",".join("?" for _ in references)
            rows = self.connection.execute(
                f"""
                SELECT entry_id, entry_type, ordinal, day_number, title, reference,
                       trajectory_key, translation, word_of_day, translation_note, theme, source_path
                FROM reconstruction_versions
                WHERE replace(reference, '-', '–') IN ({placeholders})
                ORDER BY CASE WHEN day_number IS NULL THEN 999999 ELSE day_number END DESC,
                         ordinal DESC
                LIMIT ?
                """,
                [*references, limit],
            ).fetchall()
            if rows:
                return [dict(row) for row in rows]

        if days:
            placeholders = ",".join("?" for _ in days)
            rows = self.connection.execute(
                f"""
                SELECT entry_id, entry_type, ordinal, day_number, title, reference,
                       trajectory_key, translation, word_of_day, translation_note, theme, source_path
                FROM reconstruction_versions
                WHERE day_number IN ({placeholders})
                ORDER BY ordinal DESC
                LIMIT ?
                """,
                [*days, limit],
            ).fetchall()
            if rows:
                return [dict(row) for row in rows]

        tokens = [token.strip().lower() for token in query.split() if token.strip()]
        if not tokens:
            return []
        clauses = [
            "lower(coalesce(reference, '')) LIKE ? OR lower(translation) LIKE ? OR "
            "lower(coalesce(word_of_day, '')) LIKE ? OR lower(coalesce(translation_note, '')) LIKE ? OR "
            "lower(coalesce(theme, '')) LIKE ?"
        ] * len(tokens)
        params: list[str] = []
        for token in tokens:
            pattern = f"%{token}%"
            params.extend((pattern, pattern, pattern, pattern, pattern))
        sql = (
            "SELECT entry_id, entry_type, ordinal, day_number, title, reference, trajectory_key, "
            "translation, word_of_day, translation_note, theme, source_path "
            "FROM reconstruction_versions WHERE " + " OR ".join(clauses) + " "
            "ORDER BY CASE WHEN day_number IS NULL THEN 999999 ELSE day_number END DESC, ordinal DESC LIMIT ?"
        )
        rows = self.connection.execute(sql, [*params, limit]).fetchall()
        return [dict(row) for row in rows]

    def search_concepts(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        tokens = [token.strip().lower() for token in query.split() if token.strip()]
        if not tokens:
            return []
        clauses = ["lower(name) LIKE ? OR lower(description) LIKE ?"] * len(tokens)
        params: list[str] = []
        for token in tokens:
            pattern = f"%{token}%"
            params.extend((pattern, pattern))
        sql = (
            "SELECT id, name, description, confidence, payload_json FROM concepts WHERE "
            + " OR ".join(clauses)
            + " ORDER BY confidence DESC LIMIT ?"
        )
        rows = self.connection.execute(sql, [*params, limit]).fetchall()
        return [
            {
                "id": r["id"], "name": r["name"], "description": r["description"],
                "confidence": r["confidence"], "payload": json.loads(r["payload_json"]),
            }
            for r in rows
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

    def retrieve_context(
        self,
        query: str,
        *,
        concept_limit: int = 6,
        evidence_limit: int = 12,
        reconstruction_limit: int = 8,
    ) -> dict[str, Any]:
        concepts = self.search_concepts(query, limit=concept_limit)
        relations: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for concept in concepts:
            for relation in self.related_concepts(concept["id"]):
                key = (relation["subject_id"], relation["predicate"], relation["object_id"])
                if key not in seen:
                    seen.add(key)
                    relations.append(relation)
        evidence = self.retriever.search(query, limit=evidence_limit)
        reconstructions = self.search_reconstructions(query, limit=reconstruction_limit)
        return {
            "concepts": concepts,
            "relations": relations,
            "evidence": evidence,
            "reconstructions": reconstructions,
        }

    def close(self) -> None:
        self.connection.close()
