TITLE = "Atlas Research"

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB = Path(__file__).parent / "web"
app = FastAPI(title=TITLE, version="1.0.0")
app.mount("/assets", StaticFiles(directory=WEB), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "project": TITLE}


import os, uuid
from pydantic import BaseModel, Field
from fastapi import HTTPException
from fastapi.responses import Response
from app.services.workflow import build_graph
from app.infrastructure.repository import Reports
from app.infrastructure.providers import model_name
from openai import APIStatusError, APITimeoutError

reports = Reports()
graph = build_graph()


class Question(BaseModel):
    topic: str = Field(min_length=5, max_length=400)


@app.get("/api/config")
def config():
    return {
        "mode": os.getenv("RESEARCH_MODE", "demo"),
        "live_ready": bool(os.getenv("NVIDIA_API_KEY", "").strip()),
        "provider": "NVIDIA NIM",
        "model": model_name(),
        "source_provider": "Wikipedia API (no search key required)",
        "stages": 5,
    }


@app.get("/api/reports")
def list_reports():
    return reports.list()


@app.post("/api/research")
def run(body: Question):
    mode = os.getenv("RESEARCH_MODE", "demo")
    if mode not in {"demo", "live"}:
        raise HTTPException(400, "RESEARCH_MODE must be demo or live")
    if mode == "live" and not os.getenv("NVIDIA_API_KEY", "").strip():
        raise HTTPException(
            503,
            "Add NVIDIA_API_KEY on the server to enable live research. Demo mode needs no key.",
        )
    try:
        state = graph.invoke(
            {"topic": body.topic, "mode": mode, "trace": []}, {"recursion_limit": 10}
        )
    except APITimeoutError as exc:
        raise HTTPException(
            504, "NVIDIA timed out. Try again later; free endpoints may be busy."
        ) from exc
    except APIStatusError as exc:
        detail = {
            401: "NVIDIA rejected the API key. Check NVIDIA_API_KEY.",
            403: "NVIDIA model access is unavailable for this account.",
            402: "NVIDIA free access or credits are exhausted. No paid fallback was attempted.",
            404: "NVIDIA model is unavailable. Choose a current free model in NVIDIA_MODEL.",
            429: "NVIDIA's free endpoint is rate limited. Wait before retrying.",
        }.get(exc.status_code, "NVIDIA inference is temporarily unavailable.")
        raise HTTPException(503, detail) from exc
    except ValueError as exc:
        raise HTTPException(
            502,
            "Research could not obtain valid source evidence or model JSON. Try a shorter topic.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502, "Research failed. Check provider configuration and server logs."
        ) from exc
    id = str(uuid.uuid4())
    reports.save(id, state)
    return {"id": id, **state}


@app.get("/api/reports/{id}")
def get_report(id: str):
    result = reports.get(id)
    if not result:
        raise HTTPException(404, "Report not found")
    return {"id": id, **result}


@app.get("/api/reports/{id}/download")
def download(id: str):
    state = reports.get(id)
    if not state:
        raise HTTPException(404, "Report not found")
    return Response(
        state["report"],
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="research-report.md"'},
    )
