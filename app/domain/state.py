from typing import TypedDict


class ResearchState(TypedDict, total=False):
    topic: str
    mode: str
    sources: list[dict]
    findings: list[dict]
    report: str
    trace: list[dict]
    verification: dict
