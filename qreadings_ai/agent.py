"""High-level QREADINGS agent facade."""

from __future__ import annotations

from typing import Any

from .engine import ReconstructionEngine
from .memory import Memory
from .model import ModelAdapter


class QReadingsAgent:
    """Run investigations while keeping the engine and memory separate."""

    def __init__(self, model: ModelAdapter, memory: Memory | None = None) -> None:
        self.engine = ReconstructionEngine()
        self.engine.attach_model(model)
        self.engine.register_model_pipeline()
        self.memory = memory

    def investigate(self, input_text: str, *, max_steps: int = 32) -> dict[str, Any]:
        state = self.engine.start(input_text)
        state = self.engine.run(state, max_steps=max_steps)
        snapshot = self.engine.snapshot(state)
        if self.memory is not None:
            self.memory.save_state(
                state.investigation_id,
                state.input_text,
                snapshot,
            )
        return snapshot
