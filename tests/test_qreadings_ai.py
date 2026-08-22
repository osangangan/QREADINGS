from qreadings_ai import ReconstructionEngine
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
