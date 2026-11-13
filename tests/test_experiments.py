from app.experiments import run


def test_offline_release_gates(tmp_path):
    record, path = run(tmp_path)
    assert record["passed"] and path.exists()
    assert len(record["configuration"]["corpus_sha256"]) == 64
    assert record["metrics"]["fabricated_citations_rejected"] == 1
