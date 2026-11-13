import time
from langgraph.graph import StateGraph, START, END
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.domain.state import ResearchState
from app.infrastructure.providers import research, synthesize, check_entailment


def event(state, node, detail, start):
    return state.get("trace", []) + [
        {
            "agent": node,
            "detail": detail,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    ]


def retrieve(state):
    start = time.perf_counter()
    sources = research(state["topic"], state["mode"])
    return {
        "sources": sources,
        "trace": event(
            state, "Research agent", f"Retrieved {len(sources)} source records", start
        ),
    }


def analyse(state):
    start = time.perf_counter()
    sources = state["sources"]
    texts = [s["text"] for s in sources]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts + [state["topic"]])
    scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
    ranked = sorted(
        [
            {**s, "relevance": round(float(score), 4)}
            for s, score in zip(sources, scores)
        ],
        key=lambda s: -s["relevance"],
    )
    return {
        "sources": ranked,
        "trace": event(
            state,
            "Analysis agent",
            "Ranked evidence with local TF-IDF retrieval",
            start,
        ),
    }


def summarize(state):
    start = time.perf_counter()
    if state["mode"] == "demo":
        findings = [
            {
                "claim": s["text"].split(". ")[0] + ".",
                "source_id": s["id"],
                "evidence": s["text"].split(". ")[0] + ".",
            }
            for s in state["sources"][:4]
        ]
    else:
        findings = synthesize(state["topic"], state["sources"][:6])
    return {
        "findings": findings,
        "trace": event(
            state,
            "Summary agent",
            f"Prepared {len(findings)} candidate findings",
            start,
        ),
    }


def verify(state):
    start = time.perf_counter()
    sources = {s["id"]: s for s in state["sources"]}
    accepted = []
    rejected = []
    for f in state["findings"]:
        source = sources.get(f.get("source_id"))
        quote = f.get("evidence", "")
        if (
            source
            and len(quote) > 15
            and quote in source["text"]
            and isinstance(f.get("claim"), str)
        ):
            accepted.append(
                {
                    **f,
                    "verification": "Citation and verbatim evidence validated; semantic truth not independently verified",
                }
            )
        else:
            rejected.append(f)
    if state.get("mode") == "live" and accepted:
        supported = check_entailment(accepted, state["sources"])
        rejected.extend(f for i, f in enumerate(accepted) if i not in supported)
        accepted = [
            {
                **f,
                "verification": "Citation and excerpt validated; separate LLM entailment pass accepted",
            }
            for i, f in enumerate(accepted)
            if i in supported
        ]
    return {
        "findings": accepted,
        "verification": {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "scope": "Citation and excerpt matching; live mode adds a separate LLM entailment review. Not independent factual verification",
        },
        "trace": event(
            state,
            "Evidence-check agent",
            f"{len(accepted)} accepted; {len(rejected)} rejected",
            start,
        ),
    }


def report(state):
    start = time.perf_counter()
    lines = ["# " + state["topic"], "", "Mode: " + state["mode"], "", "## Findings", ""]
    for f in state["findings"]:
        lines.extend(
            [f["claim"] + " [" + f["source_id"] + "]", "> " + f["evidence"], ""]
        )
    lines.extend(
        ["## Sources", ""]
        + [f"[{s['id']}] {s['title']} — {s['url']}" for s in state["sources"]]
    )
    lines.extend(
        [
            "",
            "## Limitations",
            "Offline demo uses a fixed retrieval-focused corpus and extractive summaries. Live mode retrieves Wikipedia introductory excerpts and uses NVIDIA NIM for synthesis and a separate entailment review. Wikipedia is a secondary source; coverage and excerpts can be incomplete. Evidence matching and model review do not establish real-world truth. No tools are invoked by source text.",
        ]
    )
    return {
        "report": "\n".join(lines),
        "trace": event(
            state,
            "Report agent",
            "Composed report with source identifiers and limitations",
            start,
        ),
    }


def build_graph():
    graph = StateGraph(ResearchState)
    for name, fn in [
        ("retrieve", retrieve),
        ("analyse", analyse),
        ("summarize", summarize),
        ("verify", verify),
        ("report", report),
    ]:
        graph.add_node(name, fn)
    for a, b in [
        (START, "retrieve"),
        ("retrieve", "analyse"),
        ("analyse", "summarize"),
        ("summarize", "verify"),
        ("verify", "report"),
        ("report", END),
    ]:
        graph.add_edge(a, b)
    return graph.compile()
