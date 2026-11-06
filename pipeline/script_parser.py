"""Parsing of documentary script markdown.

One parser is used for LLM output, offline stub output and hand-written scripts,
so the tests exercise the same code path the live pipeline uses.

Script format::

    ## Chapter 1: Origins
    [VISUAL: a wide shot of a 19th-century workshop]
    The first prototype ran in 1888 [S3]. It weighed almost nothing [S1].

    [VISUAL: close-up of the mechanism]
    ...

* ``## Chapter N: Title`` starts a chapter (``## Title`` also works).
* ``[VISUAL: ...]`` marks a shot change. The narration that follows a cue is
  spoken while that image is on screen, which is how scene durations are
  derived at assembly time.
* ``[S1]`` / ``[S1, S2]`` are citation markers resolved against the research
  brief by the fact checker. They are stripped before text is sent to TTS.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .models import Chapter, Script, VisualCue

VISUAL_RE = re.compile(r"\[\s*VISUAL\s*:\s*(.+?)\s*\]", re.IGNORECASE | re.DOTALL)
MARKER_RE = re.compile(r"\[\s*(S\d+(?:\s*[,;]\s*S?\d+)*)\s*\]", re.IGNORECASE)
CHAPTER_RE = re.compile(
    r"^\s*#{1,6}\s*(?:Chapter\s+(\d+)\s*[:.\-–—]\s*)?(.+?)\s*$", re.IGNORECASE
)
NARRATOR_LABEL_RE = re.compile(r"^\s*(?:Narrator|VO|V\.O\.|Voiceover)\s*:\s*", re.IGNORECASE)


def extract_citation_ids(text: str) -> List[str]:
    """Return the citation ids referenced in ``text``, in order, deduplicated."""
    ids: List[str] = []
    for match in MARKER_RE.finditer(text):
        for part in re.split(r"[,;]", match.group(1)):
            part = part.strip().upper()
            if not part:
                continue
            if not part.startswith("S"):
                part = "S" + part
            if part not in ids:
                ids.append(part)
    return ids


def strip_citation_markers(text: str) -> str:
    """Remove citation markers so TTS does not read "S one" aloud."""
    cleaned = MARKER_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    # A marker removed mid-sentence leaves "bronze ." — tighten it.
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def count_words(text: str) -> int:
    return len(strip_citation_markers(text).split())


def split_blocks(markdown: str) -> List[Tuple[str, str]]:
    """Split chapter markdown into ordered ``("cue"|"text", value)`` blocks."""
    blocks: List[Tuple[str, str]] = []
    cursor = 0
    for match in VISUAL_RE.finditer(markdown):
        prose = markdown[cursor : match.start()]
        for chunk in _prose_chunks(prose):
            blocks.append(("text", chunk))
        blocks.append(("cue", match.group(1).strip()))
        cursor = match.end()
    for chunk in _prose_chunks(markdown[cursor:]):
        blocks.append(("text", chunk))
    return blocks


def _prose_chunks(raw: str) -> List[str]:
    chunks: List[str] = []
    for para in re.split(r"\n\s*\n", raw):
        para = para.strip()
        if not para:
            continue
        lines = []
        for line in para.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or set(line) <= set("-*_ "):
                continue
            line = NARRATOR_LABEL_RE.sub("", line)
            lines.append(line)
        text = " ".join(lines).strip()
        if text:
            chunks.append(text)
    return chunks


def parse_chapter(
    markdown: str,
    index: int,
    title: str = "",
    raw: Optional[str] = None,
) -> Chapter:
    """Parse one chapter's markdown into a :class:`Chapter`."""
    blocks = split_blocks(markdown)

    narration_parts: List[str] = []
    cues: List[VisualCue] = []
    current: Optional[VisualCue] = None

    for kind, value in blocks:
        if kind == "cue":
            current = VisualCue(
                id=f"ch{index:02d}_cue{len(cues) + 1:03d}",
                chapter_index=index,
                order=len(cues) + 1,
                text=value,
                image_prompt=value,
                narrator_words=0,
            )
            cues.append(current)
        else:
            narration_parts.append(value)
            if current is not None:
                current.narrator_words += count_words(value)

    narration = "\n\n".join(narration_parts).strip()
    # A chapter with prose but no cues still needs one shot to sit on.
    if not cues and narration:
        cues.append(
            VisualCue(
                id=f"ch{index:02d}_cue001",
                chapter_index=index,
                order=1,
                text=f"establishing shot for {title or 'the chapter'}",
                image_prompt=f"establishing shot for {title or 'the chapter'}",
                narrator_words=count_words(narration),
            )
        )

    return Chapter(index=index, title=title, narration=narration, cues=cues)


def parse_script_markdown(markdown: str, topic: str = "") -> Script:
    """Parse a full script document containing ``## Chapter ...`` headings."""
    lines = markdown.splitlines()
    title = topic
    chapters: List[Chapter] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_lines
        if current_title is not None:
            idx = len(chapters) + 1
            chapters.append(
                parse_chapter("\n".join(current_lines), idx, current_title, "\n".join(current_lines))
            )
        current_lines = []

    for line in lines:
        if line.lstrip().startswith("#"):
            match = CHAPTER_RE.match(line)
            if line.lstrip().startswith("## ") or re.match(r"^\s*#+\s*Chapter\b", line, re.I):
                flush()
                current_title = match.group(2) if match else line.strip("# ").strip()
            elif not title:
                title = line.strip("# ").strip()
            continue
        if current_title is not None:
            current_lines.append(line)
    flush()

    script = Script(topic=topic or title, title=title, chapters=chapters)
    return script


def build_script(
    topic: str,
    titles: List[str],
    chapter_markdown: List[str],
    provider: str = "",
    model: str = "",
    settings=None,
) -> Script:
    """Combine per-chapter markdown into a :class:`Script`."""
    chapters = [
        parse_chapter(markdown, idx, title, markdown)
        for idx, (title, markdown) in enumerate(zip(titles, chapter_markdown), start=1)
    ]
    script = Script(
        topic=topic,
        title=titles[0] if titles else topic,
        chapters=chapters,
        target_minutes=getattr(settings, "target_minutes", 30.0),
        words_per_minute=getattr(settings, "words_per_minute", 140),
        provider=provider,
        model=model,
        offline=provider.startswith("offline"),
    )
    return script


def script_from_markdown_file(path: str, topic: str = "") -> Script:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_script_markdown(fh.read(), topic)


__all__ = [
    "VISUAL_RE",
    "MARKER_RE",
    "extract_citation_ids",
    "strip_citation_markers",
    "count_words",
    "split_blocks",
    "parse_chapter",
    "parse_script_markdown",
    "build_script",
    "script_from_markdown_file",
]
