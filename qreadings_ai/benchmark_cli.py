"""CLI for the QREADINGS retrieval benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import evaluate_contexts, load_benchmark
from .memory import Memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the QREADINGS retrieval benchmark.")
    parser.add_argument("--db", default="qreadings_ai.db", help="SQLite database path")
    parser.add_argument(
        "--benchmark",
        default="benchmarks/qreadings_reasoning_v0.json",
        help="Benchmark JSON path",
    )
    args = parser.parse_args()

    memory = Memory(args.db)
    try:
        benchmark = load_benchmark(Path(args.benchmark))
        results = evaluate_contexts(memory, benchmark)
        summary = {
            "tasks": len(results),
            "passed": sum(1 for result in results if result["pass"]),
            "average_required_coverage": (
                sum(result["required_coverage"] for result in results) / len(results)
                if results else 0.0
            ),
            "average_preservation_coverage": (
                sum(result["preservation_coverage"] for result in results) / len(results)
                if results else 0.0
            ),
            "results": results,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        memory.close()


if __name__ == "__main__":
    main()
