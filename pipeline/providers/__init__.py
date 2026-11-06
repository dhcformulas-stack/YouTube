"""Provider registry and selection rules.

Selection is explicit and testable: :func:`select_providers` returns the concrete
provider for each capability given a :class:`~pipeline.config.Settings`, plus a
record of why. Rules:

* ``offline`` mode always wins — every stage gets its deterministic stub.
* Otherwise each stage picks the first provider whose key is present, in a fixed
  preference order, and records the fallback reason.
* If a stage has no usable provider, :class:`ProviderUnavailable` is raised. We
  never silently substitute a stub for a paying customer's video.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..config import Settings
from .base import (
    ImageProvider,
    NarrationProvider,
    ProviderUnavailable,
    ResearchProvider,
    ScriptProvider,
)
from .images import OfflineImageProvider, OpenAIImageProvider
from .narration import (
    ElevenLabsNarrationProvider,
    OfflineNarrationProvider,
    OpenAITTSNarrationProvider,
)
from .research import (
    OfflineResearchProvider,
    OpenAIResearchProvider,
    PerplexityResearchProvider,
)
from .script import OfflineScriptProvider, OpenAIScriptProvider


@dataclass
class ProviderPlan:
    research: ResearchProvider
    script: ScriptProvider
    narration: NarrationProvider
    images: ImageProvider
    offline: bool = False
    notes: List[str] = field(default_factory=list)

    def describe(self) -> Dict[str, object]:
        return {
            "offline": self.offline,
            "research": {"provider": self.research.name, "model": getattr(self.research, "model", "")},
            "script": {"provider": self.script.name, "model": getattr(self.script, "model", "")},
            "narration": {
                "provider": self.narration.name,
                "model": getattr(self.narration, "model", ""),
            },
            "images": {"provider": self.images.name, "model": getattr(self.images, "model", "")},
            "notes": self.notes,
        }


def _missing(stage: str, options: List[str]) -> ProviderUnavailable:
    return ProviderUnavailable(
        f"No {stage} provider configured. Set one of: {', '.join(options)} "
        f"(or run with --offline / PIPELINE_OFFLINE=1 for a stubbed run)."
    )


def select_research(settings: Settings, notes: List[str]) -> ResearchProvider:
    if settings.offline:
        return OfflineResearchProvider(settings)
    if settings.perplexity_api_key:
        return PerplexityResearchProvider(settings)
    if settings.openai_api_key:
        notes.append(
            "research: PERPLEXITY_API_KEY unset — falling back to OpenAI "
            f"{settings.openai_research_model} without live web search"
        )
        return OpenAIResearchProvider(settings)
    raise _missing("research", ["PERPLEXITY_API_KEY", "OPENAI_API_KEY"])


def select_script(settings: Settings, notes: List[str]) -> ScriptProvider:
    if settings.offline:
        return OfflineScriptProvider(settings)
    if settings.openai_api_key:
        return OpenAIScriptProvider(settings)
    raise _missing("script", ["OPENAI_API_KEY"])


def select_narration(settings: Settings, notes: List[str]) -> NarrationProvider:
    if settings.offline:
        return OfflineNarrationProvider(settings)
    if settings.elevenlabs_api_key:
        return ElevenLabsNarrationProvider(settings)
    if settings.openai_api_key:
        notes.append(
            "narration: ELEVENLABS_API_KEY unset — falling back to OpenAI TTS "
            f"{settings.openai_tts_model}"
        )
        return OpenAITTSNarrationProvider(settings)
    raise _missing("narration", ["ELEVENLABS_API_KEY", "OPENAI_API_KEY"])


def select_images(settings: Settings, notes: List[str]) -> ImageProvider:
    if settings.offline:
        return OfflineImageProvider(settings)
    if settings.openai_api_key:
        return OpenAIImageProvider(settings)
    raise _missing("images", ["OPENAI_API_KEY"])


def select_providers(settings: Settings) -> ProviderPlan:
    notes: List[str] = []
    if settings.offline:
        notes.append("offline mode: every stage uses a deterministic stub; output is not publishable")
    plan = ProviderPlan(
        research=select_research(settings, notes),
        script=select_script(settings, notes),
        narration=select_narration(settings, notes),
        images=select_images(settings, notes),
        offline=settings.offline,
        notes=notes,
    )
    return plan


__all__ = [
    "ProviderPlan",
    "ProviderUnavailable",
    "select_providers",
    "select_research",
    "select_script",
    "select_narration",
    "select_images",
    "OfflineResearchProvider",
    "OfflineScriptProvider",
    "OfflineNarrationProvider",
    "OfflineImageProvider",
    "PerplexityResearchProvider",
    "OpenAIResearchProvider",
    "OpenAIScriptProvider",
    "ElevenLabsNarrationProvider",
    "OpenAITTSNarrationProvider",
    "OpenAIImageProvider",
]
