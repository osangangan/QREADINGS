"""Controlled comparison harness for small-model QREADINGS experiments.

The harness keeps the benchmark questions identical across three conditions:

1. bare        - model receives only the user task;
2. rag         - model receives task + retrieved source context;
3. qreadings   - model receives task + bounded context + QREADINGS protocol.

No fine-tuning is performed here. The purpose is to establish a clean baseline
before training changes the model's behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path
from typing import Any

from .benchmark import load_benchmark
from .memory import Memory
from .model import ModelAdapter
from .protocol import SYSTEM_RULES, build_stage_prompt
from .state import InvestigationState, Stage


@dataclass
class ModelEvaluationResult:
    task_id: str
    mode: str
    prompt_chars: int
    output_chars: int
    latency_seconds: float
    output: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mode": self.mode,
            "prompt_chars": self.prompt_chars,
            "output_chars": self.output_chars,
            "latency_seconds": round(self.latency_seconds, 4),
            "output": self.output,
        }


def _bare_prompt(task: dict[str, Any]) -> str:
    return (
        "Answer the following research question faithfully. "
        "Distinguish uncertainty from established claims.\n\n"
        f"QUESTION:\n{task['query']}"
    )


def _rag_prompt(task: dict[str, Any], context: dict[str, Any]) -> str:
    return (
        "Answer the following research question using only the supplied QREADINGS "
        "retrieved context. Preserve provenance and uncertainty.\n\n"
        f"QUESTION:\n{task['query']}\n\n"
        f"RETRIEVED CONTEXT:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _qreadings_prompt(task: dict[str, Any], context: dict[str, Any]) -> str:
    state = InvestigationState(
        input_text=task["query"],
        stage=Stage.DISCOURSE_STRUCTURE,
    )
    return build_stage_prompt(state, context).replace(
        "Current stage: discourse_structure",
        "Current stage: evidence_and_reconstruction",
    )


def build_prompt(mode: str, task: dict[str, Any], context: dict[str, Any]) -> str:
    if mode == "bare":
        return _bare_prompt(task)
    if mode == "rag":
        return _rag_prompt(task, context)
    if mode == "qreadings":
        return _qreadings_prompt(task, context)
    raise ValueError(f"Unknown evaluation mode: {mode}")


def evaluate_model(
    model: ModelAdapter,
    memory: Memory,
    benchmark_path: str | Path,
    *,
    modes: tuple[str, ...] = ("bare", "rag", "qreadings"),
    max_tokens: int = 512,
) -> list[ModelEvaluationResult]:
    benchmark = load_benchmark(benchmark_path)
    results: list[ModelEvaluationResult] = []

    for task in benchmark.get("tasks", []):
        context = memory.retrieve_context(task["query"])
        for mode in modes:
            prompt = build_prompt(mode, task, context)
            started = time.perf_counter()
            output = model.generate(prompt, max_tokens=max_tokens)
            elapsed = time.perf_counter() - started
            results.append(
                ModelEvaluationResult(
                    task_id=str(task["id"]),
                    mode=mode,
                    prompt_chars=len(prompt),
                    output_chars=len(output),
                    latency_seconds=elapsed,
                    output=output,
                )
            )
    return results


def save_results(results: list[ModelEvaluationResult], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps([item.as_dict() for item in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
