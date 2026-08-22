from qreadings_ai.memory import Memory
from qreadings_ai.state import Evidence, Hypothesis


def test_memory_retrieves_concepts_and_relations(tmp_path):
    memory = Memory(tmp_path / "memory.db")
    a = memory.upsert_concept(
        "relation",
        "A conceptual operation connecting entities.",
        confidence=0.8,
    )
    b = memory.upsert_concept(
        "belonging",
        "A relational state of being connected within a system.",
        confidence=0.7,
    )
    memory.add_relation(a, "supports", b, weight=0.9)

    context = memory.retrieve_context("relational operation")

    assert context["concepts"]
    assert any(item["object_id"] == b for item in context["relations"])
    memory.close()


def test_memory_persists_evidence_and_hypothesis(tmp_path):
    memory = Memory(tmp_path / "memory.db")
    evidence = Evidence(content="Observed form", source="corpus", strength=0.9)
    hypothesis = Hypothesis(claim="Candidate reconstruction", confidence=0.6)

    memory.add_evidence("inv-1", evidence)
    memory.add_hypothesis("inv-1", hypothesis)

    evidence_count = memory.connection.execute(
        "SELECT COUNT(*) AS n FROM evidence WHERE investigation_id = ?",
        ("inv-1",),
    ).fetchone()["n"]
    hypothesis_count = memory.connection.execute(
        "SELECT COUNT(*) AS n FROM hypotheses WHERE investigation_id = ?",
        ("inv-1",),
    ).fetchone()["n"]

    assert evidence_count == 1
    assert hypothesis_count == 1
    memory.close()
