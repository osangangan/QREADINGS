# QREADINGS AI

A low-bloat cognitive architecture built from the QREADINGS Reconstruction Engine.

## Design principle

The language model is a component, not the entire intelligence. The engine owns:

- explicit investigation state;
- sequential and iterative execution;
- uncertainty;
- hypotheses and evidence;
- controlled backtracking;
- persistent lightweight memory.

A local quantised LLM can later be attached to individual stage handlers without changing the core architecture.

## MVP

The current implementation provides:

1. An explicit `InvestigationState`.
2. The eleven-stage QREADINGS pipeline.
3. Stage handlers that can be replaced by deterministic or neural modules.
4. Explicit backtracking support.
5. A SQLite memory layer suitable for constrained hardware.

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

- structured lexical and corpus memory;
- hypothesis scoring and validation;
- a model adapter for local GGUF inference;
- QREADINGS-specific prompt/protocol contracts;
- evaluation fixtures based on existing case studies.
