from qreadings_ai.benchmark import evaluate_retrieval


def test_benchmark_requires_all_required_evidence():
    task = {
        "id": "x",
        "must_retrieve": ["alpha", "beta"],
        "must_preserve": ["provisional"],
    }
    result = evaluate_retrieval({"evidence": ["alpha provisional"]}, task)

    assert result["required_hits"] == ["alpha"]
    assert result["required_misses"] == ["beta"]
    assert result["preservation_coverage"] == 1.0
    assert result["pass"] is False


def test_benchmark_passes_complete_context():
    task = {
        "id": "x",
        "must_retrieve": ["alpha", "beta"],
        "must_preserve": ["provisional", "revision"],
    }
    result = evaluate_retrieval({"evidence": ["alpha beta provisional revision"]}, task)

    assert result["pass"] is True
