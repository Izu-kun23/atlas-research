# Verification record

Verified on 13 November 2026 with Python 3.12.

- 14 pytest regression tests passed, including mocked NVIDIA wire-protocol and Wikipedia retrieval tests.
- Python source compilation passed.
- DOM integration checks passed for rendered metrics, primary form submission, result rendering, error states, text escaping and button reset.
- All notebook code cells executed in an isolated IPython process and saved with outputs. Socket-based Jupyter kernels were unavailable in the build environment; the notebooks retain a normal Python 3 kernelspec for local Jupyter use.
- Browser connection timed out; pixel-level browser rendering and mobile interactions have not been visually verified. Responsive CSS breakpoints are implemented.
- HTTP integration tests use FastAPI TestClient. No public deployment is included.

## Measured results

Offline graph completes five stages, reviews four fixed source records and retains four extractive findings. Unknown source IDs and fabricated excerpts are rejected in regression tests. A mocked live entailment pass also filters unsupported interpretations. **At the original build**, no live NVIDIA inference request had been executed. Live credentials were configured and verified later; see docs/live-nvidia-validation.json. MockTransport tests verify the real SDK request URL, model, JSON response validation and source retrieval without API charges. No claim of general factual accuracy is made.

## Reproduce

Install `requirements.lock`, then run `python -m pytest -q`. Install Node 24+, run `npm ci && npm run test:ui`. Open the notebook in Jupyter and run all cells. See README for ports and configuration.

## Notebook and Tailwind update

Three substantive notebooks (16 executed code cells) now cover baseline analysis, deeper experiments and operational audits. All code cells executed with saved outputs; no error outputs remain. Tailwind CSS 4.3.5 builds successfully. DOM workflow checks pass after the UI changes. GitHub notebook inclusion is explicitly enabled without overriding its detected language; only compiler-generated CSS is marked generated.

## MLOps update

Release fingerprints, experiment gates, bounded operational telemetry and fresh-kernel notebook CI are implemented. Validation records are generated under ignored `artifacts/`; they are not claims that GitHub CI has executed. See `docs/mlops.md` for exact scope and deployment limits.

Real hosted NVIDIA inference was subsequently verified with two completion IDs and six retrieved sources. The runtime key is held only in the private Site secret configuration.

Final MLOps validation: 3 notebooks, 17 executed code cells; regression tests and project evaluation gates pass locally. Hosted Atlas uses real NVIDIA inference; provider completion IDs are recorded separately from mocked tests.

## Federated source release

21 Python tests and 11 Worker tests passed. UI checks passed for reports, source links, notebook outputs and Specs navigation. The updated audit notebook executed eight code cells. Live endpoint probes confirmed HTTP 200 from web-search RSS, Crossref and Europe PMC; deployed-provider coverage is recorded with the live canary separately.
