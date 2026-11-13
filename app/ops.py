"""Release provenance and bounded, payload-free operational measurements."""

import hashlib, importlib.metadata, json, os, sqlite3, subprocess, time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def file_digest(path):
    return digest(Path(path).read_bytes())


def code_digest():
    files = sorted((ROOT / "app").rglob("*.py"))
    return digest(
        b"".join(
            str(p.relative_to(ROOT)).encode() + b"\0" + p.read_bytes() + b"\0"
            for p in files
        )
    )


@lru_cache(maxsize=1)
def release_info():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = os.getenv("SOURCE_COMMIT", "unknown")
    packages = {}
    for name in [
        "fastapi",
        "numpy",
        "pandas",
        "scikit-learn",
        "xgboost",
        "shap",
        "langgraph",
        "openai",
    ]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {
        "project": json.loads((ROOT / "ops/policy.json").read_text())["project"],
        "operations_policy_sha256": file_digest(ROOT / "ops/policy.json"),
        "release_version": "1.1.0",
        "git_commit": commit,
        "application_sha256": code_digest(),
        "dependency_lock_sha256": file_digest(ROOT / "requirements-runtime.lock"),
        "analysis_lock_sha256": file_digest(ROOT / "requirements.lock"),
        "data_files": {
            str(p.relative_to(ROOT)): file_digest(p)
            for p in sorted((ROOT / "data").glob("*.json"))
        },
        "packages": packages,
    }


def save_run(output, configuration, metrics, gates, extra=None):
    from uuid import uuid4

    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    run = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid4().hex[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "release": release_info(),
        "configuration": configuration,
        "configuration_sha256": digest(canonical(configuration)),
        "metrics": metrics,
        "gates": gates,
        "passed": all(gates.values()),
        **(extra or {}),
    }
    destination = path / (run["run_id"] + ".json")
    with destination.open("x") as stream:
        json.dump(run, stream, indent=2, allow_nan=False)
    return run, destination


class ObservationStore:
    def __init__(self, path=None):
        self.path = str(path or os.getenv("OPS_DB", ROOT / "data/observations.db"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,route TEXT,status INTEGER,duration_ms REAL,created TEXT DEFAULT CURRENT_TIMESTAMP)"
            )

    def record(self, route, status, duration_ms):
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute(
                "INSERT INTO observations(route,status,duration_ms) VALUES(?,?,?)",
                (route, status, duration_ms),
            )
            db.execute(
                "DELETE FROM observations WHERE id <= (SELECT coalesce(max(id),0)-10000 FROM observations)"
            )

    def summary(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT route,status,duration_ms FROM observations ORDER BY id DESC LIMIT 1000"
            ).fetchall()
        durations = sorted(r[2] for r in rows)
        errors = sum(r[1] >= 500 for r in rows)
        n = len(rows)
        p95 = durations[min(int(0.95 * (n - 1)), n - 1)] if n else 0
        policy = json.loads((ROOT / "ops/policy.json").read_text())
        alerts = []
        if n >= policy["minimum_monitoring_samples"]:
            if errors / max(n, 1) > policy["maximum_error_rate"]:
                alerts.append("server_error_rate")
            if p95 > policy["p95_latency_budget_ms"]:
                alerts.append("latency")
        return {
            "window": "latest 1000 requests",
            "requests": n,
            "server_errors": errors,
            "server_error_rate": errors / max(n, 1),
            "p95_latency_ms": round(p95, 3),
            "alerts_evaluated": n >= policy["minimum_monitoring_samples"],
            "alerts": alerts,
            "policy": policy,
            "retention_limit": 10000,
            "stored_fields": ["route template", "status code", "duration", "timestamp"],
            "quality_scope": "operational signals only; predictive or factual quality requires independent labels",
        }


def install_operations(app):
    store = ObservationStore()

    @app.middleware("http")
    async def observe(request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            if request.url.path.startswith("/api/") and request.url.path not in {
                "/api/ops",
                "/api/version",
            }:
                route = getattr(request.scope.get("route"), "path", "unmatched")
                try:
                    store.record(route, status, (time.perf_counter() - started) * 1000)
                except sqlite3.Error:
                    pass  # Metrics must not take down serving.

    @app.get("/api/version")
    def version():
        return release_info()

    @app.get("/api/ops")
    def operations():
        return store.summary()

    return store
