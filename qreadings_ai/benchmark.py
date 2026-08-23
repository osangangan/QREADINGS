"""Lightweight benchmark utilities for the QREADINGS cognitive architecture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any



def load_benchmark(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))



def _normalised_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False).lower()


def _preservation_tokens(context: dict[str, Any]) -> set[str]:
    """Expose structured labels alongside retrieved prose for fidelity scoring."""
    tokens: set[str] = set()

    for evidence in context.get("evidence", []):
        evidence_type = str(evidence.get("evidence_type", "")).lower().strip()
        source_path = str(evidence.get("source_path", "")).lower().strip()
        metadata = evidence.get("metadata") or {}
        metadata_json = evidence.get("metadata_json") or {}
        if evidence_type:
            tokens.add(evidence_type)
            tokens.add(evidence_type.replace("_", " "))
        if source_path:
            tokens.add("research log" if "research_log/" in source_path else source_path)
        if metadata_json and isinstance(metadata_json, str):
            try:
                parsed = json.loads(metadata_json)
                if isinstance(parsed, dict):
                    metadata.update(parsed)
            except json.JSONDecodeError:
                pass
        for key, value in metadata.items():
            key_norm = str(key).lower().strip()
            value_norm = str(value).lower().strip()
            if key_norm:
                tokens.add(key_norm)
                tokens.add(key_norm.replace("_", " "))
            if value_norm:
                tokens.add(value_norm)
                tokens.add(value_norm.replace("_", " "))
        if evidence_type == "corpus_record":
            tokens.update({"source record", "explicit field"})
        if evidence_type == "reconstruction_version":
            tokens.update({"historical reconstruction", "provenance"})

    for reconstruction in context.get("reconstructions", []):
        entry_type = str(reconstruction.get("entry_type", "")).lower()
        tokens.add("historical reconstruction")
        tokens.add("provenance")
        if entry_type == "possible_readings":
            tokens.add("possible reading")
            tokens.add("alternative")
        if reconstruction.get("translation_note"):
            tokens.update({"translation note", "reasoning", "reason for choice"})
        if reconstruction.get("word_of_day"):
            tokens.add("lexical distinction")
        if reconstruction.get("day_number") is not None:
            tokens.add("chronology")
        if reconstruction.get("theme"):
            tokens.add("theme")

    return tokens


def evaluate_retrieval(context: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Score observable retrieval coverage and preservation metadata."""
    corpus = _normalised_context(context)
    structured = _preservation_tokens(context)
    required = [str(item).lower() for item in task.get("must_retrieve", [])]
    preserved = [str(item).lower() for item in task.get("must_preserve", [])]

    required_hits = [item for item in required if item in corpus]
    preserved_hits = [item for item in preserved if item in corpus or item in structured]

    required_score = len(required_hits) / len(required) if required else 1.0
    preserved_score = len(preserved_hits) / len(preserved) if preserved else 1.0

    return {
        "task_id": task.get("id"),
        "required_hits": required_hits,
        "required_misses": [item for item in required if item not in required_hits],
        "preserved_hits": preserved_hits,
        "preserved_misses": [item for item in preserved if item not in preserved_hits],
        "required_coverage": required_score,
        "preservation_coverage": preserved_score,
        "pass": required_score == 1.0 and preserved_score == 1.0,
    }



def evaluate_contexts(memory: Any, benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for task in benchmark.get("tasks", []):
        context = memory.retrieve_context(task["query"])
        results.append(evaluate_retrieval(context, task))
    return results
