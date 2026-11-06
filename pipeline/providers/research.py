"""Research providers: produce a sourced research brief.

Order of preference when a run is online:

1. Perplexity (``PERPLEXITY_API_KEY``) — chat completions with live web search,
   returns a ``citations`` array we map to :class:`Citation` records.
2. OpenAI (``OPENAI_API_KEY``) — same JSON brief, but *without* live web search.
   The brief is marked ``web_search=False`` so the fact-check report can say so.
3. Offline stub (``--offline`` / ``PIPELINE_OFFLINE=1``) — deterministic
   placeholder facts. Placeholder citations carry no URL and are explicitly
   marked, so nothing looks like a real source.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ..config import Settings
from ..models import Citation, Fact, ResearchBrief
from .base import ProviderError, ResearchProvider, post_json

BRIEF_SCHEMA = """{
  "summary": "2-4 sentence overview of the topic",
  "facts": [
    {"text": "one verifiable factual statement", "date": "YYYY or YYYY-MM-DD or empty", "sources": [1]}
  ],
  "timeline": [{"date": "YYYY-MM-DD", "event": "what happened"}]
}
`"sources"` is a list of 1-based indices into the numbered source list you were
given. Every fact MUST reference at least one source index that actually
supports it. Never invent a source, a URL, a date or a number."""

SYSTEM_PROMPT = (
    "You are a meticulous historical and scientific researcher for a documentary "
    "studio. You only report facts you can support with a cited source. If a "
    "detail is uncertain or disputed, say so in the fact text. You never "
    "fabricate sources, URLs, dates or statistics. You reply with JSON only."
)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull the first JSON object out of an LLM reply."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _brief_from_payload(
    payload: Dict[str, Any],
    topic: str,
    sources: List[Dict[str, str]],
    provider: str,
    model: str,
    raw: str,
    web_search: bool,
) -> ResearchBrief:
    citations: List[Citation] = []
    for idx, src in enumerate(sources, start=1):
        citations.append(
            Citation(
                id=f"S{idx}",
                title=src.get("title") or src.get("url") or f"Source {idx}",
                url=src.get("url", ""),
                publisher=src.get("publisher", ""),
                published=src.get("published", ""),
            )
        )
    by_index = {idx: c.id for idx, c in enumerate(citations, start=1)}

    facts: List[Fact] = []
    for item in payload.get("facts", []) or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        ids = []
        for ref in item.get("sources", []) or []:
            try:
                cid = by_index.get(int(ref))
            except (TypeError, ValueError):
                cid = None
            if cid:
                ids.append(cid)
        facts.append(Fact(text=text, date=str(item.get("date", "")).strip(), citation_ids=ids))

    timeline: List[Dict[str, str]] = []
    for item in payload.get("timeline", []) or []:
        if isinstance(item, dict) and item.get("event"):
            timeline.append(
                {
                    "date": str(item.get("date", "")).strip(),
                    "event": str(item.get("event", "")).strip(),
                }
            )

    brief = ResearchBrief(
        topic=topic,
        summary=str(payload.get("summary", "")).strip(),
        facts=facts,
        timeline=timeline,
        citations=citations,
        provider=provider,
        model=model,
        raw=raw,
    )
    # Recorded on the brief so the manifest can distinguish web-grounded
    # research from a model answering from memory.
    brief.__dict__["web_search"] = web_search
    return brief


class PerplexityResearchProvider(ResearchProvider):
    name = "perplexity"
    requires_key = "PERPLEXITY_API_KEY"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.perplexity_model

    def research(self, topic: str, criteria: str = "") -> ResearchBrief:
        prompt = (
            f"Research the topic: {topic}\n"
            f"Audience/constraints: {criteria or 'general audience, documentary tone'}\n\n"
            "Return JSON matching exactly this shape:\n"
            f"{BRIEF_SCHEMA}\n\n"
            "Provide 20-40 facts, each with the source index that supports it. "
            "Cite only sources you actually used."
        )
        data = post_json(
            "https://api.perplexity.ai/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            headers={
                "Authorization": f"Bearer {self.settings.perplexity_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        content = data["choices"][0]["message"]["content"]
        payload = _extract_json(content)
        if payload is None:
            raise ProviderError("Perplexity returned no parseable JSON brief")

        # Perplexity returns `citations` (list of URLs) or `search_results`
        # (list of {title, url, date}) depending on model/version.
        sources: List[Dict[str, str]] = []
        for item in data.get("search_results", []) or []:
            sources.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "published": item.get("date", ""),
                }
            )
        if not sources:
            for url in data.get("citations", []) or []:
                sources.append({"title": url, "url": url})
        return _brief_from_payload(
            payload, topic, sources, self.name, self.model, content, web_search=True
        )


class OpenAIResearchProvider(ResearchProvider):
    """Fallback research provider. No live web search — facts come from the model."""

    name = "openai"
    requires_key = "OPENAI_API_KEY"
    web_search = False

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.openai_research_model

    def research(self, topic: str, criteria: str = "") -> ResearchBrief:
        prompt = (
            f"Research the topic: {topic}\n"
            f"Audience/constraints: {criteria or 'general audience, documentary tone'}\n\n"
            "Return JSON matching exactly this shape:\n"
            f"{BRIEF_SCHEMA}\n\n"
            "Use only facts you are confident are correct, and cite each fact with "
            "the numbered source you used. Include a `sources` array of "
            '{"title": ..., "url": ..., "publisher": ...} objects. If you cannot '
            "supply a real URL for a source, leave the url empty rather than "
            "inventing one."
        )
        data = post_json(
            f"{self.settings.openai_base_url}/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        content = data["choices"][0]["message"]["content"]
        payload = _extract_json(content)
        if payload is None:
            raise ProviderError("OpenAI returned no parseable JSON brief")
        sources = [s for s in payload.get("sources", []) or [] if isinstance(s, dict)]
        return _brief_from_payload(
            payload, topic, sources, self.name, self.model, content, web_search=False
        )


class OfflineResearchProvider(ResearchProvider):
    """Deterministic stub. Clearly labelled — contains no real sources."""

    name = "offline"
    model = "offline-stub"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    def research(self, topic: str, criteria: str = "") -> ResearchBrief:
        citations = [
            Citation(
                id=f"S{i}",
                title=f"OFFLINE PLACEHOLDER source {i} (not a real source)",
                url="",
                placeholder=True,
            )
            for i in range(1, 4)
        ]
        beats = [
            "the origin and early context",
            "the central development",
            "the people and institutions involved",
            "the scientific or technical mechanism",
            "contemporary evidence and records",
            "the turning point",
            "the consequences",
            "the long-term legacy",
            "how it is understood today",
            "open questions that remain",
        ]
        facts = [
            Fact(
                text=f"[OFFLINE PLACEHOLDER] Claim about {topic} regarding {beat}.",
                date="",
                citation_ids=[f"S{(i % len(citations)) + 1}"],
            )
            for i, beat in enumerate(beats)
        ]
        brief = ResearchBrief(
            topic=topic,
            summary=(
                f"[OFFLINE PLACEHOLDER] Deterministic stub brief for '{topic}'. "
                "No real research was performed and none of these sources exist."
            ),
            facts=facts,
            timeline=[
                {"date": "0000", "event": "[OFFLINE PLACEHOLDER] Timeline entry"},
            ],
            citations=citations,
            provider=self.name,
            model=self.model,
            offline=True,
            raw="",
        )
        brief.__dict__["web_search"] = False
        return brief


__all__ = [
    "PerplexityResearchProvider",
    "OpenAIResearchProvider",
    "OfflineResearchProvider",
]
