"""Stage 4 — narration (text-to-speech, per chapter).

Each chapter is synthesised to its own audio file so a failed chapter can be
retried without re-billing the whole video, and so chapter audio duration is the
authoritative timing source for assembly.
"""

from __future__ import annotations

import os
from typing import List, Tuple

from .config import Settings
from .models import ChapterAudio, Script, dump_json
from .providers import ProviderPlan


def audio_duration(path: str, ffprobe_bin: str = "ffprobe") -> float:
    """Duration in seconds via ffprobe (accurate for mp3 and wav)."""
    import subprocess

    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr[:300]}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned no duration for {path}") from exc


def narration_text(chapter_text: str) -> str:
    """Text as it should be spoken: citation markers removed."""
    from .script_parser import strip_citation_markers

    return strip_citation_markers(chapter_text)


def run_narration(
    script: Script,
    settings: Settings,
    plan: ProviderPlan,
    out_dir: str,
) -> Tuple[List[ChapterAudio], str]:
    """Synthesise one audio file per chapter. Returns tracks and manifest path."""
    audio_dir = os.path.join(out_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    tracks: List[ChapterAudio] = []

    for chapter in script.chapters:
        text = narration_text(chapter.narration)
        if not text.strip():
            text = f"Chapter {chapter.index}: {chapter.title}."
        extension = "wav" if plan.narration.name.startswith("offline") else "mp3"
        path = os.path.join(audio_dir, f"chapter_{chapter.index:02d}.{extension}")
        plan.narration.synthesize(text, path)
        tracks.append(
            ChapterAudio(
                chapter_index=chapter.index,
                path=path,
                duration=round(audio_duration(path), 3),
                characters=len(text),
                provider=plan.narration.name,
            )
        )

    manifest_path = os.path.join(out_dir, "narration.json")
    dump_json(
        {
            "provider": plan.narration.name,
            "model": getattr(plan.narration, "model", ""),
            "total_duration": round(sum(t.duration for t in tracks), 3),
            "chapters": [t.__dict__ for t in tracks],
        },
        manifest_path,
    )
    return tracks, manifest_path


__all__ = ["run_narration", "audio_duration", "narration_text"]
