"""Minimal SQLite memory layer.

The MVP deliberately avoids heavyweight infrastructure. Structured state is kept
in SQLite so it can remain useful on an 8 GB laptop.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


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

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                strength REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hypotheses (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                claim TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_investigation
                ON evidence(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_hypotheses_investigation
                ON hypotheses(investigation_id);
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

    def close(self) -> None:
        self.connection.close()
