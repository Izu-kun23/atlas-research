"""Offline retrieval and citation-integrity release gates; never spends API credits."""

import argparse, json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.ops import ROOT, file_digest, save_run
from app.services.workflow import verify


def run(output):
    path = ROOT / "data/sources.json"
    sources = json.loads(path.read_text())
    queries = [
        ("retrieval augmented generation", "S1"),
        ("position long context", "S2"),
        ("BEIR benchmark domains", "S3"),
        ("BM25 frequency normalization", "S4"),
    ]
    reciprocal = []
    for query, expected in queries:
        vectors = TfidfVectorizer(stop_words="english").fit_transform(
            [s["text"] for s in sources] + [query]
        )
        scores = cosine_similarity(vectors[-1], vectors[:-1])[0]
        ranking = [
            s["id"] for _, s in sorted(zip(scores, sources), key=lambda pair: -pair[0])
        ]
        reciprocal.append(1 / (ranking.index(expected) + 1))
    rejected = verify(
        {
            "mode": "demo",
            "sources": sources,
            "findings": [
                {
                    "claim": "Unsupported",
                    "source_id": "missing",
                    "evidence": "This quotation does not exist in any source.",
                }
            ],
            "trace": [],
        }
    )["verification"]["rejected"]
    metrics = {
        "mrr": sum(reciprocal) / len(reciprocal),
        "fabricated_citations_rejected": rejected,
        "sources": len(sources),
    }
    gates = {
        "valid_unique_source_ids": len({s["id"] for s in sources}) == len(sources),
        "nonempty_evidence": all(len(s["text"]) > 40 for s in sources),
        "mrr_at_least_075": metrics["mrr"] >= 0.75,
        "fabricated_citation_rejected": rejected == 1,
    }
    config = {
        "corpus_sha256": file_digest(path),
        "representation": "word TF-IDF cosine similarity",
        "queries": queries,
        "mode": "offline evaluation",
        "scope": "provenance mechanics, not factual accuracy",
    }
    return save_run(output, config, metrics, gates)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="artifacts/runs")
    args = p.parse_args()
    record, path = run(args.output)
    print(
        json.dumps(
            {
                "record": str(path),
                "passed": record["passed"],
                "metrics": record["metrics"],
            },
            indent=2,
        )
    )
    raise SystemExit(0 if record["passed"] else 1)


if __name__ == "__main__":
    main()
