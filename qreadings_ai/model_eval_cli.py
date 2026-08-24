"""CLI for controlled small-model comparisons."""

from __future__ import annotations

import argparse

from .memory import Memory
from .model import LlamaCppModel
from .model_eval import evaluate_model, save_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare bare, ordinary-RAG, and QREADINGS model conditions."
    )
    parser.add_argument("--db", default="qreadings_ai.db")
    parser.add_argument(
        "--benchmark",
        default="benchmarks/qreadings_reasoning_v0.json",
    )
    parser.add_argument("--model", required=True, help="Path to a local GGUF model")
    parser.add_argument("--output", default="model_eval_results.json")
    parser.add_argument("--ctx", type=int, default=2048)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--gpu-layers", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args()

    model = LlamaCppModel(
        args.model,
        n_ctx=args.ctx,
        n_threads=args.threads,
        n_batch=args.batch,
        n_gpu_layers=args.gpu_layers,
    )
    memory = Memory(args.db)
    try:
        results = evaluate_model(
            model,
            memory,
            args.benchmark,
            max_tokens=args.max_tokens,
        )
        save_results(results, args.output)
        print(f"Saved {len(results)} evaluations to {args.output}")
    finally:
        memory.close()


if __name__ == "__main__":
    main()
