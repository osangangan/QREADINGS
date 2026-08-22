from qreadings_ai.memory import Memory


def test_evidence_retrieval_preserves_provenance(tmp_path):
    memory = Memory(tmp_path / "test.db")
    memory.add_passage(
        "research_log/INV0008.md",
        "Hypothesis",
        "Lexical families may primarily encode primitive conceptual operations.",
        evidence_type="hypothesis",
        metadata={"status": "provisional"},
    )
    memory.add_passage(
        "specification/Specification.md",
        "Core Axioms",
        "Ambiguity shall be preserved where the Arabic preserves ambiguity.",
        evidence_type="specification",
    )

    result = memory.retrieve_context("conceptual operations")

    assert result["evidence"]
    top = result["evidence"][0]
    assert top["source_path"] == "research_log/INV0008.md"
    assert top["evidence_type"] == "hypothesis"
    assert top["score"] > 0
    memory.close()
