# QREADINGS AI

A low-bloat cognitive architecture built from the QREADINGS Reconstruction Engine.

## Design principle

The language model is a component, not the entire intelligence. The engine owns:

- explicit investigation state;
- sequential and iterative execution;
- uncertainty;
- hypotheses and evidence;
- controlled backtracking;
- persistent lightweight memory;
- provenance-aware retrieval;
- longitudinal reconstruction history.

A local quantised LLM can later be attached to individual stage handlers without changing the core architecture.

## MVP

The current implementation provides:

1. An explicit `InvestigationState`.
2. The eleven-stage QREADINGS pipeline.
3. Stage handlers that can be replaced by deterministic or neural modules.
4. Explicit backtracking support.
5. A SQLite memory layer suitable for constrained hardware.
6. Conservative repository ingestion for QREADINGS source material.
7. Provenance-aware evidence retrieval.
8. A reconstruction-trajectory store for longitudinal translation history.

## Longitudinal translation history

QREADINGS translation history is treated as a sequence of provisional reconstruction states rather than a flat collection of answers.

Each parsed entry retains:

- entry type and day number;
- Qur'anic reference;
- translation text;
- Word of the Day material;
- translation notes;
- themes where explicitly stated;
- raw source text;
- provenance;
- a trajectory key for repeated references.

This preserves the evolution of the project without declaring later readings automatically correct.

## Ingestion

Repository ingestion remains conservative and does not use an LLM to infer concepts during the first pass.

```bash
python -m qreadings_ai.ingest . --db qreadings_ai.db
```

A separate translation-history document can be included without committing the document itself to the repository:

```bash
python -m qreadings_ai.ingest . --db qreadings_ai.db \
  --translation-history "/path/to/365 Days of Q.txt"
```

The resulting SQLite database is disposable derived state. The Git repository remains the source corpus.

## Example

```python
from qreadings_ai import ReconstructionEngine

engine = ReconstructionEngine()
state = engine.start("Example input")
state = engine.run(state)
print(engine.snapshot(state))
```

The default handlers intentionally do not invent analysis. They return an explicit unimplemented result until a specialist handler is registered.

## Next architectural layer

The next implementation should add:

- hypothesis scoring and validation;
- evaluation fixtures derived from QREADINGS case studies and translation history;
- semantic retrieval as an optional layer over lexical retrieval;
- a local GGUF model runtime;
- model-training traces generated from reconstruction trajectories.
