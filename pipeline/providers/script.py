"""Script providers: turn a research brief into a documentary script.

The script is generated in two passes so long-form output does not get truncated:

1. ``outline()`` — one call that returns chapter titles.
2. ``write_chapter()`` — one call per chapter, asking for narrator lines with
   ``[VISUAL: ...]`` cues and inline citation markers (``[S1]``) that point back
   at the research brief.

Citation markers are what makes the fact-check stage meaningful: every factual
sentence in the finished script must carry one.
"""

from __future__ import annotations

from typing import List

from ..config import Settings
from ..models import ResearchBrief, Script
from .base import ProviderError, ScriptProvider, post_json

FORMAT_RULES = """Output format — follow it exactly:

- Start with one `[VISUAL: ...]` line describing the shot that opens the chapter.
- Then narrator prose. Plain sentences, no speaker labels, no stage directions.
- End every factual sentence with citation markers for the sources that support
  it, e.g. `The first prototype ran in 1947 [S3].` Multiple: `[S1][S4]`.
- Put a new `[VISUAL: ...]` line wherever the picture should change (roughly
  every 60-90 spoken words).
- Never invent a source index that is not in the brief. Never state a fact you
  cannot tie to a source index. If the brief does not support a detail, leave
  it out.
- No headings, no markdown bold, no word counts, no commentary about the task."""

SYSTEM_PROMPT = (
    "You are a documentary scriptwriter for a premium YouTube history and "
    "science channel. You write accurate, cinematic, narrator-voiced prose in "
    "present tense. You never invent facts, dates, numbers or sources."
)


def _brief_digest(brief: ResearchBrief) -> str:
    lines = [f"TOPIC: {brief.topic}", "", f"SUMMARY: {brief.summary}", "", "SOURCES:"]
    for citation in brief.citations:
        lines.append(f"  {citation.id}: {citation.title} ({citation.url or 'no url'})")
    lines.append("")
    lines.append("FACTS (each tagged with the sources that support it):")
    for fact in brief.facts:
        refs = " ".join(f"[{cid}]" for cid in fact.citation_ids) or "[UNCITED]"
        date = f" ({fact.date})" if fact.date else ""
        lines.append(f"  - {fact.text}{date} {refs}")
    if brief.timeline:
        lines.append("")
        lines.append("TIMELINE:")
        for entry in brief.timeline:
            lines.append(f"  - {entry.get('date', '')}: {entry.get('event', '')}")
    return "\n".join(lines)


class OpenAIScriptProvider(ScriptProvider):
    name = "openai"
    requires_key = "OPENAI_API_KEY"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.script_model

    def _chat(self, prompt: str, max_tokens: int) -> str:
        data = post_json(
            f"{self.settings.openai_base_url}/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.settings.script_temperature,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:  # pragma: no cover - defensive
            raise ProviderError(f"Unexpected script response shape: {exc}") from exc

    def outline(self, brief: ResearchBrief, chapter_count: int) -> List[str]:
        prompt = (
            f"{_brief_digest(brief)}\n\n"
            f"Plan a {chapter_count}-chapter documentary arc for the topic above. "
            "Chapter 1 must be the hook, the last chapter must be the legacy and "
            "closing. Reply with one chapter title per line, numbered like "
            "'1. Title'. No other text."
        )
        text = self._chat(prompt, 600)
        titles: List[str] = []
        for raw in text.splitlines():
            line = raw.strip().lstrip("-*0123456789. )").strip()
            if line:
                titles.append(line)
        if not titles:
            raise ProviderError("Script outline returned no chapter titles")
        return titles[:chapter_count]

    def write_chapter(
        self,
        brief: ResearchBrief,
        titles: List[str],
        chapter_index: int,
        target_words: int,
        target_minutes: float,
    ) -> str:
        title = titles[chapter_index - 1]
        prompt = (
            f"{_brief_digest(brief)}\n\n"
            f"DOCUMENTARY ARC: {' / '.join(titles)}\n\n"
            f"Write chapter {chapter_index} of {len(titles)}: \"{title}\".\n"
            f"Target {target_words} words of narrator prose "
            f"(about {target_minutes:.1f} minutes of narration).\n\n"
            f"{FORMAT_RULES}"
        )
        text = self._chat(prompt, self.settings.script_max_tokens)
        if not text.strip():
            raise ProviderError(f"Empty script returned for chapter {chapter_index}")
        return text.strip()

    def write_script(self, brief: ResearchBrief, settings: Settings) -> Script:
        from ..script_parser import build_script

        titles = self.outline(brief, settings.chapters)
        per_chapter = max(120, int(round(settings.target_words / max(1, len(titles)))))
        chapter_markdown = []
        for idx, _title in enumerate(titles, start=1):
            chapter_markdown.append(
                self.write_chapter(
                    brief,
                    titles,
                    idx,
                    per_chapter,
                    settings.target_minutes / len(titles),
                )
            )
        return build_script(
            topic=brief.topic,
            titles=titles,
            chapter_markdown=chapter_markdown,
            provider=self.name,
            model=self.model,
            settings=settings,
        )


class OfflineScriptProvider(ScriptProvider):
    """Deterministic stub script built from the offline brief.

    It exercises the exact same parser, fact-checker and assembly path as the
    live provider, so ``--offline`` is a genuine end-to-end test of the pipeline.
    """

    name = "offline"
    model = "offline-stub"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    def outline(self, brief: ResearchBrief, chapter_count: int) -> List[str]:
        beats = [
            "The Hook",
            "Origins",
            "The People Behind It",
            "How It Works",
            "The Turning Point",
            "Evidence and Records",
            "Consequences",
            "Legacy and Open Questions",
        ]
        titles = [f"{beat} — {brief.topic}" for beat in beats]
        return titles[:chapter_count]

    def write_chapter(
        self,
        brief: ResearchBrief,
        titles: List[str],
        chapter_index: int,
        target_words: int,
        target_minutes: float,
    ) -> str:
        facts = brief.facts or []
        if not facts:
            facts = brief.facts
        # Spread the brief's facts across chapters, wrapping around.
        start = (chapter_index - 1) * 2
        picked = [facts[(start + i) % len(facts)] for i in range(min(2, len(facts)))] if facts else []

        lines: List[str] = [
            f"[VISUAL: OFFLINE PLACEHOLDER establishing shot for chapter {chapter_index}, "
            f"{titles[chapter_index - 1]}]",
            "",
        ]
        filler = (
            "The record here is deliberately thin, because this is a placeholder "
            "chapter produced without a research provider."
        )
        sentences = []
        for fact in picked:
            refs = "".join(f"[{cid}]" for cid in fact.citation_ids)
            sentences.append(f"{fact.text} {refs}".strip())
        body = " ".join(sentences) if sentences else filler
        lines.append(body)
        lines.append("")
        # Pad toward the requested length with deterministic, non-factual prose.
        # A new shot every ~120 spoken words matches how a real script paces its
        # B-roll, so the offline run exercises a realistic scene count.
        written = len(body.split())
        block = 0
        while written < target_words:
            block += 1
            if block % 2 == 1:
                lines.append(
                    f"[VISUAL: OFFLINE PLACEHOLDER b-roll {block} for chapter "
                    f"{chapter_index} — {titles[chapter_index - 1]}]"
                )
                lines.append("")
            paragraph = (
                f"This is placeholder narration block {block} for chapter "
                f"{chapter_index}. It exists only so the offline pipeline produces "
                "a full-length timeline; it makes no factual claims about the "
                "subject. A real run replaces this text with researched, cited "
                "narration from the configured script provider, and the shape of "
                "the document stays exactly the same."
            )
            lines.append(paragraph)
            lines.append("")
            written += len(paragraph.split())
        return "\n".join(lines).strip()


__all__ = ["OpenAIScriptProvider", "OfflineScriptProvider"]
