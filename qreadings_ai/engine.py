"""Executable MVP of the QREADINGS reconstruction loop."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable
from uuid import uuid4

from .state import InvestigationState, Stage, Status


StageHandler = Callable[[InvestigationState], dict[str, Any]]


class ReconstructionEngine:
    """Small, model-agnostic controller for QREADINGS investigations.

    The engine owns process state. An LLM, parser, corpus tool, or other module
    can be attached later through stage handlers without changing the state model.
    """

    def __init__(self) -> None:
        self.handlers: dict[Stage, StageHandler] = {}

    def register(self, stage: Stage, handler: StageHandler) -> None:
        self.handlers[stage] = handler

    def start(self, input_text: str) -> InvestigationState:
        state = InvestigationState(input_text=input_text)
        state.record("started", investigation_id=str(uuid4()))
        return state

    def step(self, state: InvestigationState) -> InvestigationState:
        if state.status == Status.COMPLETED:
            return state

        handler = self.handlers.get(state.stage, self._default_handler)
        output = handler(state)
        state.outputs[state.stage.value] = output
        state.record("stage_completed", output=output)
        state.status = Status.RUNNING
        state.advance()
        return state

    def run(self, state: InvestigationState, max_steps: int = 32) -> InvestigationState:
        steps = 0
        while state.status != Status.COMPLETED and steps < max_steps:
            self.step(state)
            steps += 1
        if state.status != Status.COMPLETED:
            state.add_uncertainty("Investigation reached the configured execution limit.")
        return state

    @staticmethod
    def _default_handler(state: InvestigationState) -> dict[str, Any]:
        """Return an explicit placeholder rather than inventing analysis."""
        return {
            "implemented": False,
            "input": state.input_text,
            "note": "No specialist handler is registered for this stage.",
        }

    @staticmethod
    def snapshot(state: InvestigationState) -> dict[str, Any]:
        payload = asdict(state)
        payload["status"] = state.status.value
        payload["stage"] = state.stage.value
        return payload
