"""Lightweight benchmark utilities for the QREADINGS cognitive architecture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any



def load_benchmark(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))



def evaluate_retrieval(context: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Score only observable retrieval coverage; do not judge generated prose."""
    corpus = json.dumps(context, ensure_ascii=False).lower()
    required = [str(item).lower() for item in task.get("must_retrieve", [])]
    preserved = [str(item).lower() for item in task.get("must_preserve", [])]

    required_hits = [item for item in required if item in corpus]
    preserved_hits = [item for item in preserved if item in corpus]

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
