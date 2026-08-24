# Local model evaluation

The first model experiment compares the same eight benchmark tasks under three conditions:

1. `bare`: the model receives only the task question;
2. `rag`: the model receives the task plus bounded retrieved QREADINGS context;
3. `qreadings`: the model receives the task plus bounded context and the QREADINGS structured protocol.

This is a baseline experiment. It deliberately does not fine-tune the model.

## First model

Use **Qwen3-4B Q4_K_M** as the initial local model. The upstream Qwen3-4B model is Apache-2.0, and a GGUF Q4_K_M build is available from `ggml-org/Qwen3-4B-GGUF`. The Q4_K_M file is about 2.5 GB. llama.cpp supports running this GGUF directly and can use Q4_K_M as its default quantisation target. See the project README for current download/runtime commands.

The target is an 8 GB RAM laptop, so start with:

- CPU inference (`n_gpu_layers=0`)
- `n_ctx=2048`
- `n_batch=128`
- `max_tokens=512`

These are conservative starting settings, not guaranteed hardware requirements.

## Local setup

Install the optional model dependency:

```bash
python -m pip install llama-cpp-python
```

Then download the Q4_K_M GGUF and place it somewhere outside Git tracking, for example:

```text
models/Qwen3-4B-Q4_K_M.gguf
```

Do not commit the model or the generated evaluation JSON.

## Run

After the QREADINGS database has been ingested:

```bash
python -m qreadings_ai.model_eval_cli \
  --db qreadings_ai.db \
  --benchmark benchmarks/qreadings_reasoning_v0.json \
  --model "models/Qwen3-4B-Q4_K_M.gguf" \
  --output model_eval_results.json
```

The output contains one record per task and mode, with prompt size, output size, latency and raw model output.

## What we compare

The first experiment is intended to answer whether adding QREADINGS structure improves a small model relative to the same model with no retrieval or ordinary retrieval.

The later scoring layer will evaluate:

- provenance fidelity;
- uncertainty preservation;
- hypothesis separation;
- trajectory reconstruction;
- methodological-status fidelity;
- final answer quality;
- prompt/context size and latency.

Do not interpret a single benchmark score as evidence of AGI. The experiment is a controlled architectural comparison.
