import json

from qreadings_ai.ingest import ingest_repository
from qreadings_ai.memory import Memory


def test_ingest_markdown_and_json(tmp_path):
    root = tmp_path / "repo"
    (root / "research_log").mkdir(parents=True)
    (root / "corpora").mkdir(parents=True)
    (root / "research_log" / "INV0001.md").write_text(
        "# Investigation\n\n# Hypothesis\n\nA test hypothesis.",
        encoding="utf-8",
    )
    (root / "corpora" / "catalogue.json").write_text(
        json.dumps([
            {
                "verse": "1:1",
                "designation": "اللَّهِ",
                "morphology": "Proper noun",
                "immediate_context": "Praise/Invocation",
                "pairing": ["الرَّحْمَٰنِ"],
            }
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    db = tmp_path / "memory.db"
    stats = ingest_repository(root, db)

    assert stats["markdown_files"] == 1
    assert stats["json_files"] == 1
    assert stats["evidence_chunks"] >= 1
    assert stats["json_records"] == 1

    memory = Memory(db)
    try:
        concepts = memory.search_concepts("Praise/Invocation")
        assert concepts
        relations = memory.related_concepts(concepts[0]["id"])
        assert relations
    finally:
        memory.close()
