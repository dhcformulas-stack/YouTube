"""Provider interfaces and shared HTTP plumbing.

Each capability (research, script, narration, images) has one small interface so
the orchestrator never cares which vendor is behind it. Real providers talk to
the vendor REST API directly with ``requests`` — no vendor SDK, no heavyweight
dependency.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests

from ..config import Settings
from ..models import ResearchBrief, Script


class ProviderUnavailable(RuntimeError):
    """Raised when no provider can serve a stage (missing key / unknown name)."""


class ProviderError(RuntimeError):
    """Raised when a configured provider fails after retries."""


def post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: int = 180,
    retries: int = 3,
    backoff: float = 2.0,
) -> Dict[str, Any]:
    """POST JSON with bounded exponential backoff on transient failures."""
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                # 4xx other than 429 will not get better by retrying.
                if response.status_code < 500 and response.status_code != 429:
                    raise ProviderError(
                        f"{url} returned {response.status_code}: {response.text[:500]}"
                    )
                raise ProviderError(
                    f"{url} returned {response.status_code}: {response.text[:200]}"
                )
            return response.json()
        except (requests.RequestException, ProviderError, ValueError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff * attempt)
    raise ProviderError(f"POST {url} failed after {retries} attempts: {last_error}")


def post_bytes(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: int = 180,
    retries: int = 3,
    backoff: float = 2.0,
) -> bytes:
    """POST JSON and return raw bytes (used for TTS responses)."""
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise ProviderError(
                    f"{url} returned {response.status_code}: {response.text[:300]}"
                )
            return response.content
        except (requests.RequestException, ProviderError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(backoff * attempt)
    raise ProviderError(f"POST {url} failed after {retries} attempts: {last_error}")


def get_bytes(url: str, timeout: int = 180, retries: int = 3) -> bytes:
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code >= 400:
                raise ProviderError(f"GET {url} returned {response.status_code}")
            return response.content
        except (requests.RequestException, ProviderError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(2.0 * attempt)
    raise ProviderError(f"GET {url} failed after {retries} attempts: {last_error}")


# --------------------------------------------------------------------------- #
# Capability interfaces
# --------------------------------------------------------------------------- #
class ResearchProvider(ABC):
    name: str = "base"
    model: str = ""
    requires_key: str = ""

    @abstractmethod
    def research(self, topic: str, criteria: str = "") -> ResearchBrief:
        """Return a sourced research brief for ``topic``."""


class ScriptProvider(ABC):
    name: str = "base"
    model: str = ""
    requires_key: str = ""

    @abstractmethod
    def outline(self, brief: ResearchBrief, chapter_count: int) -> List[str]:
        """Return ``chapter_count`` chapter titles for the documentary."""

    @abstractmethod
    def write_chapter(
        self,
        brief: ResearchBrief,
        titles: List[str],
        chapter_index: int,
        target_words: int,
        target_minutes: float,
    ) -> str:
        """Return markdown for one chapter (narrator lines + [VISUAL: ...] cues)."""

    def write_script(self, brief: ResearchBrief, settings: Settings) -> Script:
        """Assemble a full :class:`Script` from the per-chapter calls."""
        from ..script_parser import parse_chapter

        titles = self.outline(brief, settings.chapters)
        per_chapter = max(
            120,
            int(round(settings.target_words / max(1, len(titles)))),
        )
        chapters = []
        for idx, title in enumerate(titles, start=1):
            markdown = self.write_chapter(
                brief, titles, idx, per_chapter, settings.target_minutes / len(titles)
            )
            chapters.append(parse_chapter(markdown, idx, title, markdown))
        script = Script(
            topic=brief.topic,
            title=titles[0] if titles else brief.topic,
            chapters=chapters,
            target_minutes=settings.target_minutes,
            words_per_minute=settings.words_per_minute,
            provider=self.name,
            model=self.model,
            offline=self.name.startswith("offline"),
        )
        return script


class NarrationProvider(ABC):
    name: str = "base"
    requires_key: str = ""

    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        """Write narration audio for ``text`` to ``output_path``; return the path."""


class ImageProvider(ABC):
    name: str = "base"
    model: str = ""
    requires_key: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        output_path: str,
        chapter_title: str = "",
        scene_index: int = 0,
    ) -> str:
        """Write one 16:9 image for ``prompt`` to ``output_path``."""
