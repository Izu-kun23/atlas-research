# Verification record

Verified on 13 November 2026 with Python 3.12.

- 4 pytest regression tests passed.
- Python source compilation passed.
- DOM integration checks passed for rendered metrics, primary form submission, result rendering, error states, text escaping and button reset.
- All notebook code cells executed in an isolated IPython process and saved with outputs. Socket-based Jupyter kernels were unavailable in the build environment; the notebooks retain a normal Python 3 kernelspec for local Jupyter use.
- Browser connection timed out; pixel-level browser rendering and mobile interactions have not been visually verified. Responsive CSS breakpoints are implemented.
- HTTP integration tests use FastAPI TestClient. No public deployment is included.

## Measured results

Offline graph completes five stages, reviews four fixed source records and retains four extractive findings. Unknown source IDs and fabricated excerpts are rejected in regression tests. A mocked live entailment pass also filters unsupported interpretations. **No paid/live OpenAI request was executed**; credentials are required to verify the live provider integration. No claim of general factual accuracy is made.

## Reproduce

Install `requirements.lock`, then run `python -m pytest -q`. Install Node 24+, run `npm ci && npm run test:ui`. Open the notebook in Jupyter and run all cells. See README for ports and configuration.
