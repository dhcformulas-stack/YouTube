"""Runtime configuration for the Chronicle Forge video production pipeline.

Every tunable is an environment variable so the same image can run in dev
(``PIPELINE_OFFLINE=1``, no keys) and in production (keys present) without a
code change. Secrets are never logged: :meth:`Settings.redacted` is what goes
into the run manifest.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

_TRUTHY = {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUTHY


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    """Resolved settings for one pipeline run."""

    # --- mode -------------------------------------------------------------
    offline: bool = False

    # --- research (LLM with live web citations) ---------------------------
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar-pro"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_research_model: str = "gpt-4o-mini"

    # --- script (LLM) -----------------------------------------------------
    script_model: str = "gpt-4o-mini"
    script_temperature: float = 0.7
    script_max_tokens: int = 3000

    # --- narration (TTS) --------------------------------------------------
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "onyx"
    openai_tts_format: str = "mp3"

    # --- images -----------------------------------------------------------
    image_model: str = "gpt-image-1"
    image_size: str = "1536x1024"
    image_quality: str = "medium"

    # --- video ------------------------------------------------------------
    video_width: int = 1920
    video_height: int = 1080
    video_fps: int = 30
    video_crf: int = 23
    video_preset: str = "veryfast"
    video_batch_size: int = 10
    audio_bitrate: str = "192k"
    min_scene_seconds: float = 1.5

    # --- editorial --------------------------------------------------------
    target_minutes: float = 30.0
    words_per_minute: int = 140
    chapters: int = 8

    # --- infrastructure ---------------------------------------------------
    ffmpeg_bin: str = ""
    http_timeout: int = 180
    max_retries: int = 3

    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    @property
    def target_words(self) -> int:
        """Narration word count that lands on ``target_minutes`` at WPM."""
        return int(round(self.target_minutes * self.words_per_minute))

    @classmethod
    def from_env(cls, offline_override: bool | None = None) -> "Settings":
        s = cls(
            offline=_env_flag("PIPELINE_OFFLINE", False),
            perplexity_api_key=_env("PERPLEXITY_API_KEY"),
            perplexity_model=_env("PERPLEXITY_MODEL", "sonar-pro"),
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            openai_research_model=_env("OPENAI_RESEARCH_MODEL", "gpt-4o-mini"),
            script_model=_env("SCRIPT_MODEL", _env("OPENAI_SCRIPT_MODEL", "gpt-4o-mini")),
            script_temperature=_env_float("SCRIPT_TEMPERATURE", 0.7),
            script_max_tokens=_env_int("SCRIPT_MAX_TOKENS", 3000),
            elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
            elevenlabs_model=_env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            elevenlabs_base_url=_env("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1").rstrip("/"),
            openai_tts_model=_env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=_env("OPENAI_TTS_VOICE", "onyx"),
            openai_tts_format=_env("OPENAI_TTS_FORMAT", "mp3"),
            image_model=_env("IMAGE_MODEL", _env("OPENAI_IMAGE_MODEL", "gpt-image-1")),
            image_size=_env("IMAGE_SIZE", "1536x1024"),
            image_quality=_env("IMAGE_QUALITY", "medium"),
            video_width=_env_int("VIDEO_WIDTH", 1920),
            video_height=_env_int("VIDEO_HEIGHT", 1080),
            video_fps=_env_int("VIDEO_FPS", 30),
            video_crf=_env_int("VIDEO_CRF", 23),
            video_preset=_env("VIDEO_PRESET", "veryfast"),
            video_batch_size=_env_int("VIDEO_BATCH_SIZE", 10),
            audio_bitrate=_env("AUDIO_BITRATE", "192k"),
            min_scene_seconds=_env_float("MIN_SCENE_SECONDS", 1.5),
            target_minutes=_env_float("TARGET_MINUTES", 30.0),
            words_per_minute=_env_int("WORDS_PER_MINUTE", 140),
            chapters=_env_int("CHAPTERS", 8),
            ffmpeg_bin=_env("FFMPEG_BIN"),
            http_timeout=_env_int("HTTP_TIMEOUT", 180),
            max_retries=_env_int("MAX_RETRIES", 3),
        )
        if offline_override is not None:
            s.offline = bool(offline_override)
        return s

    # ------------------------------------------------------------------ #
    def redacted(self) -> Dict[str, Any]:
        """Settings as a dict with all credentials replaced by a presence flag."""
        data = asdict(self)
        for key in list(data):
            if key.endswith("_api_key"):
                data[key] = "set" if data[key] else "unset"
        return data

    def has(self, name: str) -> bool:
        return bool(getattr(self, name, ""))
