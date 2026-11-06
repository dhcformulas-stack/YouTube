"""Dataclasses shared by every stage of the pipeline.

Keeping these in one module means the research brief, the script, the fact-check
report and the run manifest all have a single, serialisable shape that the
backend can ingest without guessing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


# --------------------------------------------------------------------------- #
# Research
# --------------------------------------------------------------------------- #
@dataclass
class Citation:
    """A source backing one or more facts in the brief.

    ``url`` may be empty ONLY for offline placeholders (``placeholder=True``);
    the fact checker treats an empty URL on a non-placeholder citation as an
    invalid/fabricated source.
    """

    id: str
    title: str
    url: str = ""
    publisher: str = ""
    published: str = ""
    placeholder: bool = False


@dataclass
class Fact:
    text: str
    date: str = ""
    citation_ids: List[str] = field(default_factory=list)


@dataclass
class ResearchBrief:
    topic: str
    summary: str = ""
    facts: List[Fact] = field(default_factory=list)
    timeline: List[Dict[str, str]] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    offline: bool = False
    raw: str = ""

    def citation_map(self) -> Dict[str, Citation]:
        return {c.id: c for c in self.citations}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Script
# --------------------------------------------------------------------------- #
@dataclass
class VisualCue:
    id: str
    chapter_index: int
    order: int
    text: str
    image_prompt: str = ""
    # Words of narration spoken while this image is on screen; used to split
    # chapter audio duration across the chapter's cues at assembly time.
    narrator_words: int = 0


@dataclass
class Chapter:
    index: int
    title: str
    narration: str = ""
    cues: List[VisualCue] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """Spoken words only — citation markers are not narration."""
        from .script_parser import count_words

        return count_words(self.narration)


@dataclass
class Script:
    topic: str
    title: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    target_minutes: float = 30.0
    words_per_minute: int = 140
    provider: str = ""
    model: str = ""
    offline: bool = False

    @property
    def word_count(self) -> int:
        return sum(c.word_count for c in self.chapters)

    @property
    def estimated_minutes(self) -> float:
        if not self.words_per_minute:
            return 0.0
        return round(self.word_count / self.words_per_minute, 2)

    def all_cues(self) -> List[VisualCue]:
        return [cue for chapter in self.chapters for cue in chapter.cues]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["word_count"] = self.word_count
        data["estimated_minutes"] = self.estimated_minutes
        return data

    def to_markdown(self) -> str:
        lines = [f"# {self.title or self.topic}", ""]
        for chapter in self.chapters:
            lines.append(f"## Chapter {chapter.index}: {chapter.title}")
            lines.append("")
            body = chapter.narration.strip()
            if body:
                lines.append(body)
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# Fact check
# --------------------------------------------------------------------------- #
@dataclass
class ClaimCheck:
    chapter_index: int
    claim: str
    citation_ids: List[str] = field(default_factory=list)
    # supported | unsupported | review
    status: str = "unsupported"
    reason: str = ""


@dataclass
class FactCheckReport:
    total_claims: int = 0
    supported: int = 0
    flagged: int = 0
    claims: List[ClaimCheck] = field(default_factory=list)
    invalid_citations: List[str] = field(default_factory=list)
    offline_placeholders: int = 0
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["flagged_claims"] = [asdict(c) for c in self.claims if c.status != "supported"]
        return data


# --------------------------------------------------------------------------- #
# Narration / assembly
# --------------------------------------------------------------------------- #
@dataclass
class ChapterAudio:
    chapter_index: int
    path: str
    duration: float
    characters: int = 0
    provider: str = ""


@dataclass
class Scene:
    index: int
    image_path: str
    chapter_index: int
    cue_text: str
    duration: float


@dataclass
class RenderResult:
    video_path: str
    duration: float
    width: int
    height: int
    fps: int
    size_bytes: int
    scene_count: int


def dump_json(data: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


__all__ = [
    "Citation",
    "Fact",
    "ResearchBrief",
    "VisualCue",
    "Chapter",
    "Script",
    "ClaimCheck",
    "FactCheckReport",
    "ChapterAudio",
    "Scene",
    "RenderResult",
    "dump_json",
    "load_json",
]
