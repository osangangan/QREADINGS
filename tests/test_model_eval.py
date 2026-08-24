import json

from qreadings_ai.memory import Memory
from qreadings_ai.model import MockModel
from qreadings_ai.model_eval import build_prompt, evaluate_model


def test_prompt_modes_are_distinct():
    task = {"id": "x", "query": "What is this?"}
    context = {"concepts": [{"name": "test"}], "evidence": [], "relations": [], "reconstructions": []}

    bare = build_prompt("bare", task, context)
    rag = build_prompt("rag", task, context)
    qreadings = build_prompt("qreadings", task, context)

    assert "RETRIEVED CONTEXT" not in bare
    assert "RETRIEVED CONTEXT" in rag
    assert "QREADINGS" in qreadings


def test_evaluate_model_runs_all_conditions(tmp_path):
    db = tmp_path / "memory.db"
    memory = Memory(db)
    benchmark = tmp_path / "benchmark.json"
    benchmark.write_text(
        json.dumps({"tasks": [{"id": "x", "query": "What is this?"}]}),
        encoding="utf-8",
    )
    try:
        results = evaluate_model(MockModel('{"ok": true}'), memory, benchmark)
        assert len(results) == 3
        assert {item.mode for item in results} == {"bare", "rag", "qreadings"}
    finally:
        memory.close()
