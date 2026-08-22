"""Explicit investigation state for the QREADINGS cognitive loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class Status(str, Enum):
    RUNNING = "running"
    BACKTRACKING = "backtracking"
    WAITING_FOR_EVIDENCE = "waiting_for_evidence"
    SUSPENDED = "suspended"
    COMPLETED = "completed"


class Stage(str, Enum):
    MORPHOLOGY = "morphological_analysis"
    GRAMMAR = "grammatical_parsing"
    CONSTITUENCY = "constituency_analysis"
    CLAUSE_BOUNDARIES = "clause_boundary_detection"
    SPEECH_ACT = "speech_act_identification"
    DISCOURSE = "discourse_structure_mapping"
    CONCEPTS = "conceptual_relation_reconstruction"
    CORPUS = "corpus_investigation"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    HYPOTHESIS_EVALUATION = "hypothesis_evaluation"
    ENGLISH_RECONSTRUCTION = "english_reconstruction"


PIPELINE: tuple[Stage, ...] = (
    Stage.MORPHOLOGY,
    Stage.GRAMMAR,
    Stage.CONSTITUENCY,
    Stage.CLAUSE_BOUNDARIES,
    Stage.SPEECH_ACT,
    Stage.DISCOURSE,
    Stage.CONCEPTS,
    Stage.CORPUS,
    Stage.HYPOTHESIS_GENERATION,
    Stage.HYPOTHESIS_EVALUATION,
    Stage.ENGLISH_RECONSTRUCTION,
)


@dataclass
class Evidence:
    content: str
    source: str
    strength: float = 0.5
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Hypothesis:
    claim: str
    confidence: float = 0.5
    supporting_evidence: list[str] = field(default_factory=list)
    contradictory_evidence: list[str] = field(default_factory=list)
    status: str = "provisional"
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class InvestigationState:
    input_text: str
    status: Status = Status.RUNNING
    stage: Stage = Stage.MORPHOLOGY
    outputs: dict[str, Any] = field(default_factory=dict)
    uncertainties: list[str] = field(default_factory=list)
    rejected_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def record(self, event: str, **data: Any) -> None:
        self.history.append({
            "event": event,
            "stage": self.stage.value,
            "status": self.status.value,
            **data,
        })

    def add_uncertainty(self, statement: str) -> None:
        if statement not in self.uncertainties:
            self.uncertainties.append(statement)

    def advance(self) -> None:
        index = PIPELINE.index(self.stage)
        if index + 1 < len(PIPELINE):
            self.stage = PIPELINE[index + 1]
        else:
            self.status = Status.COMPLETED

    def backtrack_to(self, stage: Stage, reason: str) -> None:
        self.stage = stage
        self.status = Status.BACKTRACKING
        self.record("backtrack", target=stage.value, reason=reason)
