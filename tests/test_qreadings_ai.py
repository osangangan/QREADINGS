import json

from qreadings_ai import MockModel, QReadingsAgent, ReconstructionEngine
from qreadings_ai.state import PIPELINE, Stage, Status


def test_pipeline_has_expected_qreadings_stages():
    assert len(PIPELINE) == 11
    assert PIPELINE[0] is Stage.MORPHOLOGY
    assert PIPELINE[-1] is Stage.ENGLISH_RECONSTRUCTION


def test_engine_runs_to_completion_without_inventing_analysis():
    engine = ReconstructionEngine()
    state = engine.start("test input")
    state = engine.run(state)

    assert state.status is Status.COMPLETED
    assert len(state.history) == 12  # start + 11 stages
    assert all(
        output.get("implemented") is False
        for output in state.outputs.values()
    )


def test_backtracking_is_explicit():
    engine = ReconstructionEngine()
    state = engine.start("test input")
    state.backtrack_to(Stage.GRAMMAR, "Competing parses remain unresolved")

    assert state.stage is Stage.GRAMMAR
    assert state.status is Status.BACKTRACKING
    assert state.history[-1]["event"] == "backtrack"


def test_model_pipeline_consumes_structured_output():
    response = json.dumps({
        "observations": ["observed pattern"],
        "inferences": ["candidate relation"],
        "uncertainties": ["meaning remains unresolved"],
        "evidence_requests": ["find another occurrence"],
        "hypotheses": [
            {"claim": "candidate A", "confidence": 0.7, "status": "provisional"}
        ],
    })
    agent = QReadingsAgent(MockModel(response=response))
    result = agent.investigate("test input", max_steps=1)

    assert result["stage"] == Stage.GRAMMAR.value
    assert result["outputs"][Stage.MORPHOLOGY.value]["observations"] == [
        "observed pattern"
    ]
    assert result["uncertainties"] == ["meaning remains unresolved"]
    assert result["hypotheses"][0]["claim"] == "candidate A"


def test_model_response_must_be_json():
    engine = ReconstructionEngine()
    engine.attach_model(MockModel(response="not json"))
    engine.register_model_pipeline()
    state = engine.start("test input")

    try:
        engine.step(state)
    except ValueError as exc:
        assert "valid JSON" in str(exc)
    else:
        raise AssertionError("Expected invalid model output to fail closed")
