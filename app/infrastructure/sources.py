import re
from urllib.parse import quote

import httpx

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def wikipedia(topic):
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


# Only fixed provider endpoints are contacted. Returned source URLs are links,
# never crawler targets, so search results cannot initiate internal requests.
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import urlencode, urlparse
import xml.etree.ElementTree as ET
import ipaddress


def clean(value):
    return re.sub(
        r"\s+", " ", re.sub(r"<[^>]*>", " ", unescape(str(value or "")))
    ).strip()


def safe_url(value):
    try:
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return None
        if parsed.hostname == "localhost" or parsed.hostname.endswith(".local"):
            return None
        try:
            if not ipaddress.ip_address(parsed.hostname).is_global:
                return None
        except ValueError:
            pass
        return value
    except (ValueError, TypeError):
        return None


def request(url, params, xml=False):
    with httpx.Client(
        timeout=12,
        follow_redirects=False,
        headers={
            "User-Agent": "AtlasResearch/1.0 (https://github.com/Izu-kun23/atlas-research)"
        },
    ) as client:
        with client.stream("GET", url, params=params) as response:
            if response.status_code != 200:
                raise ValueError("Source service unavailable")
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 2_000_000:
                    raise ValueError("Source response exceeded budget")
    if xml:
        if re.search(rb"<!DOCTYPE|<!ENTITY", data, re.I):
            raise ValueError("Unsafe XML")
        return ET.fromstring(data)
    import json

    return json.loads(data)


def web(topic):
    root = request(
        "https://www.bing.com/search", {"q": topic, "format": "rss", "count": 6}, True
    )
    if root.tag != "rss":
        raise ValueError("Search feed unavailable")
    return [
        {
            "title": x.findtext("title"),
            "url": x.findtext("link"),
            "text": x.findtext("description"),
            "provenance": "Bing public search RSS excerpt; search snippet, full page not retrieved",
        }
        for x in root.findall("./channel/item")[:6]
    ]


def crossref(topic):
    data = request(
        "https://api.crossref.org/works",
        {"query": topic, "rows": 6, "select": "DOI,title,abstract,URL"},
    )
    return [
        {
            "title": x.get("title", [""])[0],
            "url": x.get("URL") or "https://doi.org/" + x["DOI"],
            "text": x["abstract"],
            "doi": x.get("DOI"),
            "provenance": "Crossref publisher-deposited abstract; full article not retrieved",
        }
        for x in data.get("message", {}).get("items", [])
        if x.get("abstract")
    ]


def europepmc(topic):
    data = request(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        {"query": topic, "format": "json", "pageSize": 6, "resultType": "core"},
    )
    return [
        {
            "title": x.get("title"),
            "url": (
                "https://doi.org/" + x["doi"]
                if x.get("doi")
                else "https://europepmc.org/article/"
                + quote(x.get("source", ""), safe="")
                + "/"
                + quote(x.get("id", ""), safe="")
            ),
            "doi": x.get("doi"),
            "text": x["abstractText"],
            "provenance": "Europe PMC indexed publication abstract; full article not retrieved",
        }
        for x in data.get("resultList", {}).get("result", [])
        if x.get("abstractText")
    ]


def arxiv(topic):
    query = " ".join(re.findall(r"[a-z0-9]+", topic, re.I)[:12])
    root = request(
        "https://export.arxiv.org/api/query",
        {
            "search_query": "all:" + query,
            "start": 0,
            "max_results": 6,
            "sortBy": "relevance",
        },
        True,
    )
    ns = {"a": "http://www.w3.org/2005/Atom"}
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ValueError("Preprint feed unavailable")
    return [
        {
            "title": x.findtext("a:title", namespaces=ns),
            "url": (x.findtext("a:id", namespaces=ns) or "").replace(
                "http:", "https:", 1
            ),
            "text": x.findtext("a:summary", namespaces=ns),
            "provenance": "arXiv preprint abstract; not necessarily peer reviewed",
        }
        for x in root.findall("a:entry", ns)
    ]


def search_with_coverage(topic):
    definitions = [
        ("Web search", web),
        ("Crossref", crossref),
        ("Europe PMC", europepmc),
        ("arXiv", arxiv),
        ("Wikipedia", wikipedia),
    ]

    def run(item):
        provider, fn = item
        try:
            rows = []
            for row in fn(topic):
                row = {
                    **row,
                    "provider": provider,
                    "url": safe_url(row.get("url")),
                    "title": clean(row.get("title")),
                    "text": clean(row.get("text"))[:3500],
                }
                if row["url"] and row["title"] and len(row["text"]) >= 40:
                    rows.append(row)
            return rows, {
                "provider": provider,
                "status": "available",
                "retrieved": len(rows),
            }
        except (httpx.HTTPError, ValueError, ET.ParseError, KeyError, TypeError):
            return [], {"provider": provider, "status": "unavailable", "retrieved": 0}

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run, definitions))
    sources = []
    seen = set()
    for i in range(6):
        for rows, _ in results:
            if i >= len(rows) or len(sources) >= 12:
                continue
            row = rows[i]
            key = (row.get("doi") or row["url"].rstrip("/")).lower()
            if key in seen:
                continue
            seen.add(key)
            sources.append({**row, "id": f"S{len(sources)+1}"})
    if not sources:
        raise ValueError("No source service returned usable evidence")
    return sources, [coverage for _, coverage in results]


def search_sources(topic):
    return search_with_coverage(topic)[0]
