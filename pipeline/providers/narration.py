"""Narration providers (text-to-speech), one audio file per chapter.

Preference order when online: ElevenLabs (``ELEVENLABS_API_KEY``) then OpenAI
TTS (``OPENAI_API_KEY``). Offline mode writes silent audio of the correct
duration so the timeline, scene durations and muxing are still exercised.
"""

from __future__ import annotations

import subprocess
from typing import Optional

from ..config import Settings
from .base import NarrationProvider, ProviderError, post_bytes


class ElevenLabsNarrationProvider(NarrationProvider):
    name = "elevenlabs"
    requires_key = "ELEVENLABS_API_KEY"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.voice_id = settings.elevenlabs_voice_id
        self.model = settings.elevenlabs_model

    def synthesize(self, text: str, output_path: str) -> str:
        url = (
            f"{self.settings.elevenlabs_base_url}/text-to-speech/"
            f"{self.voice_id}?output_format=mp3_44100_128"
        )
        audio = post_bytes(
            url,
            {
                "text": text,
                "model_id": self.model,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            headers={
                "xi-api-key": self.settings.elevenlabs_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        if not audio:
            raise ProviderError("ElevenLabs returned an empty audio body")
        with open(output_path, "wb") as fh:
            fh.write(audio)
        return output_path


class OpenAITTSNarrationProvider(NarrationProvider):
    name = "openai-tts"
    requires_key = "OPENAI_API_KEY"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.openai_tts_model

    def synthesize(self, text: str, output_path: str) -> str:
        audio = post_bytes(
            f"{self.settings.openai_base_url}/audio/speech",
            {
                "model": self.model,
                "voice": self.settings.openai_tts_voice,
                "input": text,
                "response_format": self.settings.openai_tts_format,
            },
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        if not audio:
            raise ProviderError("OpenAI TTS returned an empty audio body")
        with open(output_path, "wb") as fh:
            fh.write(audio)
        return output_path


class OfflineNarrationProvider(NarrationProvider):
    """Silent audio of the correct length, generated with ffmpeg.

    Duration is estimated from the word count at the configured words-per-minute,
    so scene durations and chapter sync behave exactly as they will in
    production. There is no synthetic voice: offline audio is silent by design.
    """

    name = "offline-silence"
    requires_key = ""

    def __init__(self, settings: Settings, ffmpeg_bin: Optional[str] = None):
        self.settings = settings
        self.ffmpeg = ffmpeg_bin or settings.ffmpeg_bin or "ffmpeg"

    def synthesize(self, text: str, output_path: str) -> str:
        words = max(1, len(text.split()))
        wpm = max(60, self.settings.words_per_minute)
        duration = round(words / wpm * 60.0, 3)
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=44100",
            "-t",
            f"{duration}",
            "-c:a",
            "pcm_s16le",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProviderError(f"ffmpeg failed to write offline narration: {result.stderr[:400]}")
        return output_path


__all__ = [
    "ElevenLabsNarrationProvider",
    "OpenAITTSNarrationProvider",
    "OfflineNarrationProvider",
]
