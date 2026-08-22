"""High-level QREADINGS agent facade."""

from __future__ import annotations

from typing import Any

from .engine import ReconstructionEngine
from .memory import Memory
from .model import ModelAdapter


class QReadingsAgent:
    """Run investigations while keeping engine, model and memory separate."""

    def __init__(self, model: ModelAdapter, memory: Memory | None = None) -> None:
        self.memory = memory or Memory()
        self.engine = ReconstructionEngine(memory=self.memory)
        self.engine.attach_model(model)
        self.engine.register_model_pipeline()

    def investigate(self, input_text: str, *, max_steps: int = 32) -> dict[str, Any]:
        state = self.engine.start(input_text)
        state = self.engine.run(state, max_steps=max_steps)
        snapshot = self.engine.snapshot(state)
        self.memory.save_state(state.investigation_id, state.input_text, snapshot)
        return snapshot

    def close(self) -> None:
        self.memory.close()
