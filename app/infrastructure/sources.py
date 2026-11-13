"""Free Wikipedia source retrieval, independent of the language model.

Only a fixed HTTPS API host is contacted. URLs in retrieved text cannot trigger
requests. Evidence is the actual API excerpt, not a model-generated citation.
"""

import re
from urllib.parse import quote

import httpx

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def search_sources(topic):
    # Natural-language questions are reduced to a bounded set of search terms.
    stopwords = {
        "how",
        "what",
        "which",
        "why",
        "when",
        "where",
        "can",
        "does",
        "do",
        "the",
        "a",
        "an",
        "is",
        "are",
        "in",
        "of",
        "to",
        "and",
        "for",
        "with",
        "about",
        "should",
        "would",
        "could",
    }
    terms = [t for t in re.findall(r"[\w-]+", topic) if t.lower() not in stopwords][:8]
    if not terms:
        raise ValueError("Enter a topic containing searchable keywords")
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "generator": "search",
        "gsrsearch": " ".join(terms),
        "gsrnamespace": 0,
        "gsrlimit": 6,
        "prop": "extracts|revisions",
        "exintro": 1,
        "explaintext": 1,
        "exlimit": "max",
        "exchars": 3500,
        "rvprop": "ids|timestamp",
    }
    with httpx.Client(
        timeout=20,
        follow_redirects=False,
        headers={
            "User-Agent": "AtlasResearch/1.0 (https://github.com/Izu-kun23/atlas-research)"
        },
    ) as client:
        with client.stream("GET", WIKIPEDIA_API, params=params) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Source API did not return a successful response")
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 1_000_000:
                    raise ValueError("Source response exceeds the 1 MB budget")
    import json

    payload = json.loads(data)
    if "error" in payload:
        raise ValueError("Source search was rejected; try a more specific topic")
    pages = sorted(
        payload.get("query", {}).get("pages", []), key=lambda p: p.get("index", 999)
    )
    sources = []
    for page in pages[:6]:
        text = page.get("extract", "").strip()[:3500]
        if len(text) < 40:
            continue
        revision = next(iter(page.get("revisions", [])), {})
        title = page.get("title", "Untitled")
        rev_id = revision.get("revid")
        url = (
            f"https://en.wikipedia.org/w/index.php?oldid={int(rev_id)}"
            if rev_id
            else f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='')}"
        )
        sources.append(
            {
                "id": f"S{len(sources)+1}",
                "url": url,
                "title": title,
                "text": text,
                "provenance": "Wikipedia API introductory excerpt (CC BY-SA); secondary source, not independently fact-checked",
                "revision_timestamp": revision.get("timestamp"),
            }
        )
    if not sources:
        raise ValueError("No source excerpts found. Try a shorter, more specific topic")
    return sources
