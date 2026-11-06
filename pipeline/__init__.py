"""Chronicle Forge video production pipeline.

Stages: research -> script -> fact-check -> narration -> images -> assembly.

Every stage is served by a provider selected from environment variables (see
``pipeline/providers``), and the whole chain can run with no API keys at all via
``--offline`` / ``PIPELINE_OFFLINE=1`` for development and CI.
"""

from __future__ import annotations

__version__ = "2.0.0"

from .config import Settings
from .models import (
    Chapter,
    ChapterAudio,
    Citation,
    ClaimCheck,
    Fact,
    FactCheckReport,
    RenderResult,
    ResearchBrief,
    Scene,
    Script,
    VisualCue,
)
from .script_parser import (
    count_words,
    extract_citation_ids,
    parse_chapter,
    parse_script_markdown,
    strip_citation_markers,
)

__all__ = [
    "__version__",
    "Settings",
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
    "parse_chapter",
    "parse_script_markdown",
    "extract_citation_ids",
    "strip_citation_markers",
    "count_words",
]
