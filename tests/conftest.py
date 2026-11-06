"""Shared pytest fixtures."""

from __future__ import annotations

import os
import shutil
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pipeline.config import Settings  # noqa: E402
from pipeline.models import Chapter, Citation, Fact, ResearchBrief, Script  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_pipeline_env(monkeypatch):
    """Keep the developer's real keys out of the test run."""
    for name in (
        "PIPELINE_OFFLINE",
        "PERPLEXITY_API_KEY",
        "OPENAI_API_KEY",
        "ELEVENLABS_API_KEY",
        "FFMPEG_BIN",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def offline_settings() -> Settings:
    settings = Settings.from_env(offline_override=True)
    settings.video_width = 640
    settings.video_height = 360
    settings.video_fps = 10
    settings.video_preset = "ultrafast"
    settings.chapters = 2
    settings.target_minutes = 0.5
    return settings


@pytest.fixture
def sample_brief() -> ResearchBrief:
    return ResearchBrief(
        topic="The Antikythera Mechanism",
        summary="A bronze geared calculator from the second century BCE.",
        facts=[
            Fact(
                text="The Antikythera Mechanism was recovered from a shipwreck in 1901.",
                date="1901",
                citation_ids=["S1"],
            ),
            Fact(
                text="Its main gear train models the positions of the sun and moon.",
                citation_ids=["S2"],
            ),
        ],
        citations=[
            Citation(id="S1", title="Antikythera shipwreck", url="https://example.org/s1"),
            Citation(id="S2", title="Gear train analysis", url="https://example.org/s2"),
        ],
        provider="test",
        model="test-model",
    )


@pytest.fixture
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def small_script() -> Script:
    return Script(
        topic="Test topic",
        title="Test topic",
        chapters=[
            Chapter(
                index=1,
                title="Origins",
                narration=(
                    "The first prototype ran in 1888 [S1]. "
                    "It weighed almost nothing [S1]."
                ),
                cues=[],
            )
        ],
        words_per_minute=140,
    )
