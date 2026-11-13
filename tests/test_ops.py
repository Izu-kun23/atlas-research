from app.ops import ObservationStore, digest, canonical, release_info


def test_provenance_and_canonical_hash():
    assert digest(canonical({"a": 1, "b": 2})) == digest(canonical({"b": 2, "a": 1}))
    release = release_info()
    assert len(release["application_sha256"]) == 64
    assert len(release["dependency_lock_sha256"]) == 64


def test_monitoring_aggregates_without_payloads(tmp_path):
    store = ObservationStore(tmp_path / "ops.db")
    for _ in range(19):
        store.record("/api/example", 200, 10)
    store.record("/api/example", 503, 20)
    report = store.summary()
    assert report["requests"] == 20
    assert report["server_error_rate"] == 0.05
    assert report["alerts_evaluated"]
    assert (
        "body" not in report["stored_fields"] and "query" not in report["stored_fields"]
    )


def test_ops_api():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/api/version").status_code == 200
    assert client.get("/api/ops").status_code == 200
