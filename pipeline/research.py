"""Stage 1 — research.

Runs the configured research provider and persists the brief as JSON (machine
readable, consumed by later stages) and markdown (human review).
"""

from __future__ import annotations

import os
from typing import Tuple

from .config import Settings
from .models import ResearchBrief, dump_json
from .providers import ProviderPlan


def brief_to_markdown(brief: ResearchBrief) -> str:
    lines = [f"# Research Brief: {brief.topic}", ""]
    if brief.offline:
        lines += [
            "> **OFFLINE PLACEHOLDER** — produced without a research provider. "
            "No real research was performed and no source listed here exists.",
            "",
        ]
    lines += [
        f"Provider: `{brief.provider}`  ",
        f"Model: `{brief.model}`  ",
        f"Live web search: `{getattr(brief, 'web_search', False)}`",
        "",
        "## Summary",
        "",
        brief.summary or "_(none)_",
        "",
        "## Facts",
        "",
    ]
    for i, fact in enumerate(brief.facts, start=1):
        refs = ", ".join(fact.citation_ids) or "UNCITED"
        date = f" — {fact.date}" if fact.date else ""
        lines.append(f"{i}. {fact.text}{date}  \n   Sources: {refs}")
    if brief.timeline:
        lines += ["", "## Timeline", ""]
        for entry in brief.timeline:
            lines.append(f"- **{entry.get('date', '')}** — {entry.get('event', '')}")
    lines += ["", "## Sources", ""]
    for citation in brief.citations:
        label = citation.title
        if citation.url:
            lines.append(f"- `{citation.id}` — [{label}]({citation.url})")
        else:
            marker = " (placeholder, no URL)" if citation.placeholder else " (NO URL)"
            lines.append(f"- `{citation.id}` — {label}{marker}")
    return "\n".join(lines).rstrip() + "\n"


def run_research(
    topic: str,
    settings: Settings,
    plan: ProviderPlan,
    out_dir: str,
    criteria: str = "",
) -> Tuple[ResearchBrief, str]:
    """Run the research stage. Returns the brief and the JSON path."""
    os.makedirs(out_dir, exist_ok=True)
    brief = plan.research.research(topic, criteria)
    json_path = os.path.join(out_dir, "research_brief.json")
    md_path = os.path.join(out_dir, "research_brief.md")
    dump_json(brief.to_dict(), json_path)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(brief_to_markdown(brief))
    return brief, json_path


__all__ = ["run_research", "brief_to_markdown"]
