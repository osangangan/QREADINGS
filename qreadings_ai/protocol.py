"""QREADINGS structured protocol for asking a language model to analyse state."""

from __future__ import annotations

import json
from typing import Any

from .state import InvestigationState, Stage


SYSTEM_RULES = """You are a component inside the QREADINGS Reconstruction Engine.
Do not treat your first plausible interpretation as established fact.
Separate observation from inference.
Preserve ambiguity where evidence does not resolve it.
Use retrieved memory as supporting context, not unquestionable authority.
Historical reconstructions are evidence of prior project states, not automatic truth.
When multiple reconstructions exist, compare their provenance and revision history.
Return structured JSON only.
"""


def build_stage_prompt(
    state: InvestigationState,
    memory_context: dict[str, Any] | None = None,
) -> str:
    """Build a compact prompt from current state and bounded retrieved memory."""
    relevant_output = state.outputs.get(state.stage.value, {})
    previous = {
        key: value
        for key, value in state.outputs.items()
        if key != state.stage.value
    }

    payload = {
        "stage": state.stage.value,
        "input": state.input_text,
        "prior_outputs": previous,
        "current_output": relevant_output,
        "uncertainties": state.uncertainties,
        "evidence": [
            {
                "id": item.id,
                "source": item.source,
                "content": item.content,
                "strength": item.strength,
            }
            for item in state.evidence
        ],
        "hypotheses": [
            {
                "id": item.id,
                "claim": item.claim,
                "confidence": item.confidence,
                "status": item.status,
            }
            for item in state.hypotheses
        ],
        "retrieved_memory": memory_context or {
            "concepts": [],
            "relations": [],
            "evidence": [],
            "reconstructions": [],
        },
    }

    return (
        f"{SYSTEM_RULES}\n\n"
        f"Current stage: {state.stage.value}\n"
        "Produce the smallest useful structured result for this stage.\n"
        "Required top-level keys: observations, inferences, uncertainties, "
        "evidence_requests, hypotheses.\n\n"
        f"STATE:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def parse_structured_response(text: str) -> dict[str, Any]:
    """Parse model output and fail closed rather than silently inventing data."""
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response was not valid JSON.") from exc

    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object.")
    return value


def normalise_stage_output(stage: Stage, result: dict[str, Any]) -> dict[str, Any]:
    """Keep stage outputs predictable and bounded."""
    return {
        "stage": stage.value,
        "observations": result.get("observations", []),
        "inferences": result.get("inferences", []),
        "uncertainties": result.get("uncertainties", []),
        "evidence_requests": result.get("evidence_requests", []),
        "hypotheses": result.get("hypotheses", []),
    }
