# Atlas Research

A bounded multi-stage research assistant that retrieves sources, ranks evidence, summarizes findings, validates citation excerpts, and exports a traceable report.

![Executed notebook analysis](docs/analysis.png)

**LangGraph orchestration · TF-IDF retrieval · NVIDIA NIM inference · federated source retrieval · SQLite report history**

## What it does

- Five explicit LangGraph nodes with duration traces and bounded execution.
- Offline mode runs without credentials using a clearly labelled fixed retrieval/AI corpus.
- Live mode searches the wider web, Crossref publication abstracts, Europe PMC literature, arXiv preprints and Wikipedia references, then uses NVIDIA Nemotron to summarize and review retrieved evidence. Every record includes its original URL and provenance.
- Live mode adds a separate LLM entailment review after deterministic excerpt validation. This is a conservative second pass, not a guarantee of truth.
- Verifier rejects nonexistent source IDs and quotations absent from source records.
- Dashboard includes source provenance, recent investigations and Markdown export.
- Notebook measures workflow timing and adversarial citation-integrity checks.

## Run locally

Requires Python 3.12+. Run each project in its own virtual environment.

```bash
git clone https://github.com/Izu-kun23/atlas-research.git
cd atlas-research
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-runtime.lock
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open **http://localhost:8001**. Interactive OpenAPI documentation: **http://localhost:8001/docs**. The compiled Tailwind stylesheet is checked in, so running the app needs no Node build, CDN, cloud database or frontend keys. The responsive frontend uses semantic HTML, Tailwind CSS and browser JavaScript, served from the same origin as the API.

## Architecture

```mermaid
flowchart TD
  N0["Research topic"]
  N1["source provider"]
  N2["relevance ranker"]
  N3["summarizer"]
  N4["excerpt verifier"]
  N5["report writer"]
  N0 --> N1
  N1 --> N2
  N2 --> N3
  N3 --> N4
  N4 --> N5
```

```text
app/
  domain/          Pure data contracts and algorithms
  services/        Application workflows and model orchestration
  infrastructure/ External providers and persistence adapters
  web/             Responsive dashboard and API client
  main.py          HTTP composition root and validation
data/              Reproducible demo corpus or local runtime storage
notebooks/         Executable analysis with saved outputs
tests/             Domain and API regression tests
```

HTTP routes validate inputs and delegate to services. Domain code contains the core rules. Infrastructure handles persistence and external providers. The same functions power notebooks and the application, preventing separate analysis and serving implementations.

## API

`GET /api/config`, `GET /api/reports`, `POST /api/research` (`{"topic":"How does retrieval improve research?"}`), `GET /api/reports/{id}`, `GET /api/reports/{id}/download`

All endpoints are documented and callable in `/docs`. Errors use standard FastAPI status codes and a `detail` payload. `GET /api/health` is available for health checks.

## Notebook-led analysis and verification

```bash
python -m pip install -r requirements.lock
python -m pytest -q
# Optional DOM interaction checks (Node 24+)
npm ci
npm run test:ui
python -m pip install jupyterlab
python -m jupyter lab notebooks
```

The three notebooks in [notebooks/](notebooks/README.md) cover the baseline analysis, deeper experiments and operational audits. Open them in numerical order and choose **Run All**. Checked-in outputs are generated from real executions on bundled data, not hand-entered results. See [verification](docs/verification.md) for measured outcomes and scope.

## Configuration and limitations

Default: `RESEARCH_MODE=demo` (fully offline). Live mode uses NVIDIA's free prototype endpoint. Create a key at [NVIDIA Build](https://build.nvidia.com/settings/api-keys), then export:

```bash
export NVIDIA_API_KEY='your-nvidia-key'
export NVIDIA_MODEL='nvidia/nemotron-3.5-lightning-30b-a3b'
export RESEARCH_MODE=live
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

PowerShell: use `$env:NVIDIA_API_KEY='...'`, `$env:NVIDIA_MODEL='...'` and `$env:RESEARCH_MODE='live'`. The application does not automatically load `.env`; export variables, or install `python-dotenv` and use `uvicorn --env-file .env`.

The model's [NVIDIA catalog page](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build) lists a free endpoint as of 13 November 2026. Free prototype access is account- and rate-limited; availability can change. This is not a promise of unlimited free production hosting. There is **no automatic paid-provider fallback** and no OpenAI service call. The `openai` package is only an OpenAI-compatible HTTP client pointed at `https://integrate.api.nvidia.com/v1`.

Each live run makes one federated source retrieval request and up to two NVIDIA completions: summary and independent entailment review. Requests have token, source-size and timeout budgets, and do not automatically retry model calls. A missing key returns a setup error; exhausted access and rate limits return clear messages without exposing credentials. Keys stay on the server and must never be committed.

Source retrieval searches **Bing public web-search RSS, Crossref, Europe PMC, arXiv and Wikipedia**. Web results can include official documentation, government pages, news and other indexed websites. Coverage is bounded by each index and service availability; this is not access to every website. Bing RSS is a best-effort public feed, not a contracted search API. Reports expose per-service status and result counts. Abstracts and snippets are clearly labelled; full articles and pages are not automatically fetched. Partial outages preserve available evidence, and a total outage fails explicitly.

The local retrieval layer uses sparse TF-IDF, not an embedding database. The specialized agents are bounded processing roles in a graph, not autonomous agents with arbitrary tools. Demo findings are extractive paraphrases. Live evidence is bounded to twelve diverse sources of 3,500 characters each, selected round-robin across available providers with DOI/URL deduplication before relevance ranking. Exact quote validation establishes provenance, not semantic entailment or factual truth. Small excerpts can omit context. No fake confidence score is presented.

Local persistence lives in `data/`; runtime database/model files and secrets are excluded from git. Configuration variables are described in `.env.example`.

## Docker

```bash
docker build -t atlas-research .
docker run --rm -p 8001:8000 atlas-research
```

The container runs as a non-root user. Data is ephemeral unless a writable volume is mounted at `/app/data`. Pass explicit `-e` variables for optional providers.

## Deployment boundary

This is a functioning local portfolio application, not a multi-tenant production service. There is no authentication or per-user isolation. Keep the default localhost binding; add authentication, rate limiting, request budgets, TLS, structured observability and an egress policy before public deployment. External API usage should have spend limits. Notebook results are small-data evidence, not production benchmarks.

## Tailwind UI development

Each interface uses **Tailwind CSS 4**, compiled locally rather than loaded from a CDN. The source is `app/web/tailwind.css`; `@apply` defines rounded cards, controls, tables and dashboard chrome, while HTML utilities handle typography and layout. Each product uses one accent palette and neutral surfaces.

```bash
npm ci
npm run build:css
# Watch while editing:
npm run dev:css
```

Commit both the stylesheet source and compiled output after UI changes. GitHub correctly treats the compiled CSS as generated; executable notebooks are explicitly included in GitHub language statistics under their detected file type.

## Design and implementation

The UI includes responsive layouts, accessible form labels, loading/error states, empty states, keyboard-focus styles and safe rendering of source/user content. No analytics tracker or external font request is required.

## License

MIT · Izuchukwu Tony

## Hosted Sites adapter

`deploy/sites/worker.mjs` mirrors the hosted Cloudflare Worker inference adapter. It retrieves federated source excerpts and makes up to two real NVIDIA completions, returning completion identifiers and token usage with each report. The Worker keeps the key in the Sites runtime secret `NVIDIA_API_KEY`; the Python application uses the same variable on its server. Browser login alone does not provide a server credential.

The private preview remains on the last working deployment until its server key is configured and a live call is verified. The adapter has no mock fallback in live mode.

## MLOps operations

See [the implemented operating model](docs/mlops.md) for versioned experiments, evaluation gates, notebook CI, runtime fingerprints, monitoring and rollback. Run `python -m app.experiments --output artifacts/release` for a reproducible offline release record. Operational endpoints: `/api/version` and `/api/ops`. Docker uses `requirements-runtime.lock`; analysis and tests use `requirements.lock`.

### Research interface

The Research workspace keeps the technical stack on a dedicated Specs page. Inline citations and source URLs open their original pages. The Notebook Lab displays the three executed Jupyter notebooks with saved outputs and charts; these evaluate retrieval and evidence checks, not language-model training.
