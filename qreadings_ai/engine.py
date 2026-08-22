"""Executable MVP of the QREADINGS reconstruction loop."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from .model import ModelAdapter
from .protocol import build_stage_prompt, normalise_stage_output, parse_structured_response
from .state import Hypothesis, InvestigationState, Stage, Status


StageHandler = Callable[[InvestigationState], dict[str, Any]]


class ReconstructionEngine:
    """Small, model-agnostic controller for QREADINGS investigations.

    The engine owns process state.  An LLM, parser, corpus tool, or other module
    can be attached through stage handlers without changing the state model.
    """

    def __init__(self) -> None:
        self.handlers: dict[Stage, StageHandler] = {}
        self.model: ModelAdapter | None = None

    def register(self, stage: Stage, handler: StageHandler) -> None:
        self.handlers[stage] = handler

    def attach_model(self, model: ModelAdapter) -> None:
        """Use a language model for stages that do not have specialist handlers."""
        self.model = model

    def register_model_pipeline(self) -> None:
        """Register the model as the fallback for every unhandled stage."""
        if self.model is None:
            raise RuntimeError("Attach a model before registering the model pipeline.")
        for stage in Stage:
            self.handlers[stage] = self._model_handler

    def start(self, input_text: str) -> InvestigationState:
        state = InvestigationState(input_text=input_text)
        state.record("started")
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

    def _model_handler(self, state: InvestigationState) -> dict[str, Any]:
        if self.model is None:
            return self._default_handler(state)

        prompt = build_stage_prompt(state)
        raw = self.model.generate(prompt)
        result = parse_structured_response(raw)
        output = normalise_stage_output(state.stage, result)

        for uncertainty in output["uncertainties"]:
            if isinstance(uncertainty, str):
                state.add_uncertainty(uncertainty)

        for candidate in output["hypotheses"]:
            if isinstance(candidate, str):
                state.hypotheses.append(Hypothesis(claim=candidate))
            elif isinstance(candidate, dict) and candidate.get("claim"):
                state.hypotheses.append(
                    Hypothesis(
                        claim=str(candidate["claim"]),
                        confidence=float(candidate.get("confidence", 0.5)),
                        status=str(candidate.get("status", "provisional")),
                    )
                )

        return output

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
