# QREADINGS AI Handover Note

## Branch safety
All QREADINGS AI work in this effort is on `my-feature-branch` only. `main` has not been modified.

At the latest verified point, `my-feature-branch` was ahead of `main` and the implementation lives under `qreadings_ai/`.

## Project goal
Build a low-bloat general intelligence / reasoning architecture that can plausibly run on an 8 GB RAM laptop, using QREADINGS as the cognitive/reconstruction methodology rather than treating a small LLM as the entire intelligence.

Core principle:

`LLM -> proposes -> QREADINGS engine -> records/tests/revises -> memory -> next reasoning cycle`

## Architecture implemented

- `qreadings_ai/state.py`: explicit investigation state, stages, hypotheses, evidence, uncertainty, and backtracking.
- `qreadings_ai/engine.py`: executable 11-stage QREADINGS reconstruction engine.
- `qreadings_ai/memory.py`: SQLite memory for concepts, relations, evidence, hypotheses, reconstruction versions and retrieval.
- `qreadings_ai/retrieval.py`: provenance-aware lightweight lexical evidence retrieval.
- `qreadings_ai/ingest.py`: conservative repository ingestion; does not ask an LLM to interpret the corpus.
- `qreadings_ai/trajectory.py`: parses longitudinal QREADINGS translation history into reconstruction versions/trajectories.
- `qreadings_ai/protocol.py`: structured QREADINGS model protocol.
- `qreadings_ai/model.py`: model adapter, including optional `llama-cpp-python` GGUF support and deterministic mock model.
- `qreadings_ai/agent.py`: agent facade connecting model, engine and memory.
- `qreadings_ai/benchmark.py`: retrieval/reconstruction fidelity scoring.
- `qreadings_ai/benchmark_cli.py`: benchmark runner.
- Model evaluation harness is being built for three conditions: bare LLM, ordinary RAG, and QREADINGS architecture.

## Local corpus

The user has a local file named `365 Days of Q.txt` containing longitudinal QREADINGS translations and their evolution. It should remain local and must NOT be committed. The `.gitignore` already excludes:

- `365 Days of Q.txt`
- `qreadings_ai.db`
- `qreadings_ai/__pycache__/`
- model/evaluation artifacts as configured on the feature branch

The ingestion command is:

```bash
python -m qreadings_ai.ingest . --db qreadings_ai.db --translation-history "365 Days of Q.txt"
```

## Benchmark status

The first retrieval benchmark has 8 tasks.

Latest observed result:

- tasks: 8
- passed: 5/8
- average required coverage: 0.83125 (83.1%)
- average preservation coverage: 0.7291666666666666 (72.9%)

Passing tasks include:
- 19:24 trajectory reconstruction
- Day 5 `ayat` translation note
- Day 31/34 `sabr` trajectory
- divine-designations explicit corpus relations
- INV0008 provenance/competing hypotheses

Remaining weak areas:
- complete INV0008 research-state retrieval: Hypothesis A, Hypothesis B, Current Decision, Future Validation together
- Day 5 `nafs`: preserving the stated alternative as well as the reason for choice
- ambiguity methodology: preserve ambiguity / competing evidence / provisionality / revision together

## Current model-installation issue

User is on Windows with Python 3.13. `pip install llama-cpp-python` attempted to build from source and failed because `nmake` and the C/C++ compiler were unavailable.

The error is expected for a source build. Current llama-cpp-python PyPI documentation says a pre-built CPU wheel can be installed from the extra index:

```bash
python -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

First retry with binary-only to avoid another source build:

```bash
python -m pip install --only-binary=:all: llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

If no compatible Python 3.13 wheel is available, create a Python 3.12 virtual environment and install there; the pre-built GPU wheel documentation explicitly lists 3.10–3.12, while CPU wheel availability should be checked at installation time.

Do NOT install Visual Studio Build Tools unless the wheel route fails; the goal is to keep the laptop setup minimal.

## Intended first model

Qwen3-4B Q4_K_M GGUF was selected as the first model target because its quantised file is small enough to make an 8 GB RAM experiment plausible.

The user is currently downloading the Q4_K_M GGUF into the local `models/` directory. The exact filename/path should be confirmed before running evaluation.

## Intended experiment

Compare:

A. bare small LLM + question
B. small LLM + ordinary RAG
C. small LLM + QREADINGS retrieval + structured protocol + reconstruction state

Measure:
- retrieval fidelity
- hypothesis fidelity
- uncertainty preservation
- provenance fidelity
- final-answer quality
- context/prompt size
- latency
- RAM usage

Do NOT fine-tune the model yet. First establish the base-vs-RAG-vs-QREADINGS baseline.

## User next action

1. Try the binary-only CPU wheel command above.
2. If it reports no compatible wheel, use Python 3.12 in a dedicated venv and retry.
3. Once `llama_cpp` imports successfully and the GGUF is downloaded, run the model evaluation CLI documented in the current project files, using the exact GGUF filename.

## Important development constraint

Continue making all repository changes only on `my-feature-branch`. Never modify or merge into `main` unless the user explicitly requests it.
