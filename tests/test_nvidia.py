import json

import httpx
import pytest
from openai import OpenAI as RealOpenAI
from pydantic import ValidationError

from app.infrastructure import providers, sources


def mock_nvidia(monkeypatch, reply, finish_reason="stop", status=200):
    calls = []

    def handle(request):
        assert request.url.host == "integrate.api.nvidia.com"
        assert request.url.path == "/v1/chat/completions"
        calls.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(
                status,
                json={"error": {"message": "Provider details must stay private"}},
            )
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 0,
                "model": providers.DEFAULT_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": finish_reason,
                    }
                ],
            },
        )

    def client(**kwargs):
        assert kwargs["base_url"] == providers.NVIDIA_BASE_URL
        assert kwargs["api_key"] == "test-nvidia-key"
        assert kwargs["max_retries"] == 0
        return RealOpenAI(
            **kwargs,
            http_client=httpx.Client(
                transport=httpx.MockTransport(handle), trust_env=False
            )
        )

    monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia-key")
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    monkeypatch.setattr(providers, "OpenAI", client)
    return calls


def test_summary_calls_nvidia_and_validates_findings(monkeypatch):
    finding = {
        "claim": "Evidence is preserved.",
        "source_id": "S1",
        "evidence": "Evidence is preserved in this original source.",
    }
    calls = mock_nvidia(monkeypatch, json.dumps({"findings": [finding]}))
    assert providers.synthesize(
        "evidence", [{"id": "S1", "text": finding["evidence"]}]
    ) == [finding]
    assert calls[0]["model"] == providers.DEFAULT_MODEL
    assert calls[0]["max_tokens"] == 3000
    assert calls[0]["chat_template_kwargs"]["enable_thinking"] is False


def test_entailment_filters_invalid_indices(monkeypatch):
    mock_nvidia(monkeypatch, '{"supported_indices":[0,3,-1]}')
    assert providers.check_entailment([{"claim": "a"}], []) == {0}


@pytest.mark.parametrize(
    "reply,finish",
    [
        ('{"findings":[]}', "length"),
        ("not JSON", "stop"),
        ('{"findings":[{"claim":"missing fields"}]}', "stop"),
    ],
)
def test_invalid_model_outputs_fail_closed(monkeypatch, reply, finish):
    mock_nvidia(monkeypatch, reply, finish_reason=finish)
    with pytest.raises((ValueError, ValidationError)):
        providers.synthesize("evidence", [])


def test_missing_key_never_uses_openai_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unused-openai-key")
    with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
        providers.nvidia_client()


def test_wikipedia_preserves_real_excerpts_and_revisions(monkeypatch):
    real_client = httpx.Client

    def handle(request):
        assert request.url.host == "en.wikipedia.org"
        assert request.url.params["generator"] == "search"
        return httpx.Response(
            200,
            json={
                "query": {
                    "pages": [
                        {
                            "title": "Retrieval",
                            "index": 1,
                            "extract": "A real introductory evidence passage with sufficient detail for research.",
                            "revisions": [
                                {"revid": 123, "timestamp": "2026-11-13T00:00:00Z"}
                            ],
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr(
        sources.httpx,
        "Client",
        lambda **kwargs: real_client(
            **kwargs, transport=httpx.MockTransport(handle), trust_env=False
        ),
    )
    records = sources.search_sources("What is retrieval?")
    assert records[0]["url"] == "https://en.wikipedia.org/w/index.php?oldid=123"
    assert records[0]["text"].startswith("A real introductory")
    assert records[0]["revision_timestamp"] == "2026-11-13T00:00:00Z"


def test_empty_search_never_invents_sources(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(
        sources.httpx,
        "Client",
        lambda **kwargs: real_client(
            **kwargs,
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})),
            trust_env=False
        ),
    )
    with pytest.raises(ValueError, match="No source excerpts"):
        sources.search_sources("unfindable topic")


def test_missing_key_setup_response(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("RESEARCH_MODE", "live")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    c = TestClient(app)
    config = c.get("/api/config").json()
    assert config["provider"] == "NVIDIA NIM" and not config["live_ready"]
    assert "api_key" not in config
    response = c.post("/api/research", json={"topic": "retrieval evidence"})
    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]


def test_rate_limit_explained_without_provider_details(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.services.workflow as workflow

    mock_nvidia(monkeypatch, "", status=429)
    monkeypatch.setenv("RESEARCH_MODE", "live")
    monkeypatch.setattr(
        workflow,
        "research",
        lambda topic, mode: [
            {
                "id": "S1",
                "title": "Evidence",
                "url": "https://example.org",
                "text": "A source passage that contains enough evidence for analysis.",
            }
        ],
    )
    response = TestClient(app).post(
        "/api/research", json={"topic": "evidence analysis"}
    )
    assert response.status_code == 503
    assert "rate limited" in response.json()["detail"]
    assert "Provider details" not in response.text
