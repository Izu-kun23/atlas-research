from app.services.workflow import build_graph, verify


def test_demo_workflow():
    s = build_graph().invoke(
        {"topic": "retrieval research", "mode": "demo", "trace": []}
    )
    assert len(s["trace"]) == 5
    assert s["verification"]["accepted"] == 4
    assert "[S1]" in s["report"]


def test_fabricated_evidence_rejected():
    s = verify(
        {
            "sources": [
                {"id": "S1", "text": "Real source passage with meaningful content."}
            ],
            "findings": [
                {
                    "claim": "fake",
                    "source_id": "S2",
                    "evidence": "Fabricated content of sufficient length.",
                },
                {
                    "claim": "fake",
                    "source_id": "S1",
                    "evidence": "Another fabricated excerpt with length.",
                },
            ],
            "trace": [],
        }
    )
    assert s["verification"]["rejected"] == 2
    assert not s["findings"]


def test_api_persistence_and_export(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DB", str(tmp_path / "reports.db"))
    monkeypatch.setenv("RESEARCH_MODE", "demo")
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    assert c.get("/").status_code == 200
    r = c.post("/api/research", json={"topic": "retrieval and reliability"})
    assert r.status_code == 200
    id = r.json()["id"]
    assert c.get("/api/reports/" + id).status_code == 200
    assert (
        c.get("/api/reports/" + id + "/download")
        .headers["content-type"]
        .startswith("text/markdown")
    )
    assert c.get("/api/reports/missing").status_code == 404
    assert c.post("/api/research", json={"topic": "x"}).status_code == 422


def test_live_entailment_pass_filters_claims(monkeypatch):
    import app.services.workflow as w

    monkeypatch.setattr(w, "check_entailment", lambda findings, sources: {0})
    source = {
        "id": "S1",
        "text": "A sufficiently long source excerpt for verification.",
    }
    findings = [
        {"claim": "Supported claim", "source_id": "S1", "evidence": source["text"]},
        {
            "claim": "Unsupported interpretation",
            "source_id": "S1",
            "evidence": source["text"],
        },
    ]
    result = w.verify(
        {"mode": "live", "sources": [source], "findings": findings, "trace": []}
    )
    assert (
        result["verification"]["accepted"] == 1
        and result["verification"]["rejected"] == 1
    )
    assert result["findings"][0]["claim"] == "Supported claim"
