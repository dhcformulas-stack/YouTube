"""Stage 6 — video assembly.

Produces a real H.264/AAC MP4 with ffmpeg (via subprocess, no moviepy):

1. each chapter's narration audio is normalised to 44.1 kHz PCM wav and the
   chapters are concatenated into one continuous track;
2. each chapter's audio duration is split across that chapter's visual cues in
   proportion to how many narrator words sit under each cue, so a shot stays on
   screen exactly as long as the narration it illustrates;
3. one ffmpeg pass scales/pads every still to the output resolution, concatenates
   them on the timeline and muxes the narration underneath.

ffmpeg resolution order: ``FFMPEG_BIN`` env var, ``ffmpeg`` on ``PATH``, then the
static binary bundled by ``imageio-ffmpeg`` (pip-installable fallback for hosts
where you cannot apt-install ffmpeg).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Sequence

from .config import Settings
from .models import ChapterAudio, RenderResult, Scene, Script


class FFmpegMissing(RuntimeError):
    pass


def resolve_ffmpeg(settings: Optional[Settings] = None) -> str:
    """Return a usable ffmpeg binary path, or raise :class:`FFmpegMissing`."""
    configured = (settings.ffmpeg_bin if settings else "") or os.environ.get("FFMPEG_BIN", "")
    if configured:
        if os.path.exists(configured) or shutil.which(configured):
            return configured
        raise FFmpegMissing(f"FFMPEG_BIN points at a missing binary: {configured}")
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:  # optional pip fallback: pip install imageio-ffmpeg
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on host packages
        raise FFmpegMissing(
            "ffmpeg not found. Install it (apt-get install -y ffmpeg) or "
            "pip install imageio-ffmpeg, or set FFMPEG_BIN."
        ) from exc


def resolve_ffprobe(settings: Optional[Settings] = None) -> str:
    found = shutil.which("ffprobe")
    if found:
        return found
    ffmpeg = resolve_ffmpeg(settings)
    sibling = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if os.path.exists(sibling):
        return sibling
    # imageio-ffmpeg ships no ffprobe; fall back to ffmpeg's own reporting.
    return ""


# --------------------------------------------------------------------------- #
# Timeline
# --------------------------------------------------------------------------- #
def build_scenes(
    script: Script,
    images: Dict[str, str],
    chapter_audio: Sequence[ChapterAudio],
    settings: Settings,
) -> List[Scene]:
    """Split chapter audio duration across the chapter's cues."""
    durations = {track.chapter_index: track.duration for track in chapter_audio}
    scenes: List[Scene] = []
    index = 0

    for chapter in script.chapters:
        chapter_duration = durations.get(chapter.index, 0.0)
        cues = chapter.cues
        if not cues:
            continue
        weights = [max(0, cue.narrator_words) for cue in cues]
        if sum(weights) == 0:
            weights = [1] * len(cues)

        # Reserve the minimum per scene, then split the remainder by weight.
        floor_total = settings.min_scene_seconds * len(cues)
        if chapter_duration <= floor_total:
            per_cue = max(0.4, chapter_duration / len(cues))
            scene_durations = [per_cue] * len(cues)
        else:
            spare = chapter_duration - floor_total
            total_weight = sum(weights)
            scene_durations = [
                settings.min_scene_seconds + spare * (w / total_weight) for w in weights
            ]

        for cue, duration in zip(cues, scene_durations):
            image_path = images.get(cue.id)
            if not image_path or not os.path.exists(image_path):
                continue
            index += 1
            scenes.append(
                Scene(
                    index=index,
                    image_path=image_path,
                    chapter_index=chapter.index,
                    cue_text=cue.text,
                    duration=round(duration, 3),
                )
            )
    return scenes


def build_narration_track(
    chapter_audio: Sequence[ChapterAudio],
    out_path: str,
    settings: Optional[Settings] = None,
) -> str:
    """Normalise each chapter to PCM wav and concatenate into one track."""
    ffmpeg = resolve_ffmpeg(settings)
    workdir = tempfile.mkdtemp(prefix="narration_", dir=os.path.dirname(out_path) or None)
    normalised: List[str] = []
    try:
        for track in chapter_audio:
            target = os.path.join(workdir, f"ch{track.chapter_index:02d}.wav")
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", track.path,
                "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", target,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed normalising {track.path}: {result.stderr[:300]}"
                )
            normalised.append(target)

        list_path = os.path.join(workdir, "concat.txt")
        with open(list_path, "w", encoding="utf-8") as fh:
            for path in normalised:
                fh.write(f"file '{os.path.abspath(path)}'\n")
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy", out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed concatenating narration: {result.stderr[:300]}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return out_path


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def probe_media(path: str, settings: Optional[Settings] = None) -> dict:
    """Return duration/width/height/fps for ``path`` using ffprobe."""
    ffprobe = resolve_ffprobe(settings)
    if not ffprobe:  # pragma: no cover - only when ffprobe is absent
        return {}
    cmd = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    data: dict = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "avg_frame_rate" and "/" in value:
            num, _, den = value.partition("/")
            try:
                data["fps"] = round(float(num) / float(den), 3) if float(den) else 0.0
            except ValueError:
                pass
        elif key == "duration":
            try:
                data["duration"] = round(float(value), 3)
            except ValueError:
                pass
        elif key in ("width", "height"):
            try:
                data[key] = int(value)
            except ValueError:
                pass
    return data


def _run_ffmpeg(cmd: List[str], what: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"ffmpeg failed while {what} (exit {result.returncode}): {detail[-1500:]}"
        )


def _filter_graph(scene_count: int, settings: Settings) -> str:
    width, height, fps = settings.video_width, settings.video_height, settings.video_fps
    parts: List[str] = []
    for i in range(scene_count):
        parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},"
            f"format=yuv420p[v{i}]"
        )
    inputs = "".join(f"[v{i}]" for i in range(scene_count))
    parts.append(f"{inputs}concat=n={scene_count}:v=1:a=0[vout]")
    return ";".join(parts)


def _render_segment(scenes: Sequence[Scene], output_path: str, settings: Settings) -> str:
    """Encode one batch of stills to a silent H.264 segment."""
    ffmpeg = resolve_ffmpeg(settings)
    cmd: List[str] = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for scene in scenes:
        cmd += ["-loop", "1", "-t", f"{scene.duration:.3f}", "-i", scene.image_path]
    cmd += [
        "-filter_complex", _filter_graph(len(scenes), settings),
        "-map", "[vout]",
        "-an",
        "-c:v", "libx264",
        "-preset", settings.video_preset,
        "-crf", str(settings.video_crf),
        "-pix_fmt", "yuv420p",
        "-r", str(settings.video_fps),
        output_path,
    ]
    _run_ffmpeg(cmd, f"encoding segment {os.path.basename(output_path)}")
    return output_path


def render_video(
    scenes: Sequence[Scene],
    narration_path: str,
    output_path: str,
    settings: Settings,
) -> RenderResult:
    """Encode the final MP4. Returns measured properties of the output.

    Stills are encoded in batches (``VIDEO_BATCH_SIZE``, default 10) and the
    batches are concatenated with a stream copy. One giant filter graph holding
    hundreds of decoded 1080p frames needs gigabytes of RAM and gets OOM-killed
    on small hosts; batching keeps peak memory flat however long the video is.
    """
    if not scenes:
        raise ValueError("no scenes to render — the script produced no visual cues")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    batch_size = max(1, int(settings.video_batch_size))
    workdir = tempfile.mkdtemp(prefix="render_", dir=os.path.dirname(os.path.abspath(output_path)))
    try:
        segments: List[str] = []
        for start in range(0, len(scenes), batch_size):
            batch = scenes[start : start + batch_size]
            segment = os.path.join(workdir, f"segment_{start // batch_size:03d}.mp4")
            segments.append(_render_segment(batch, segment, settings))

        list_path = os.path.join(workdir, "segments.txt")
        with open(list_path, "w", encoding="utf-8") as fh:
            for segment in segments:
                fh.write(f"file '{os.path.abspath(segment)}'\n")

        video_track = os.path.join(workdir, "video_track.mp4")
        _run_ffmpeg(
            [
                resolve_ffmpeg(settings), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", list_path,
                "-c", "copy", video_track,
            ],
            "concatenating segments",
        )

        _run_ffmpeg(
            [
                resolve_ffmpeg(settings), "-hide_banner", "-loglevel", "error", "-y",
                "-i", video_track,
                "-i", narration_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", settings.audio_bitrate,
                "-movflags", "+faststart",
                "-shortest",
                output_path,
            ],
            "muxing narration",
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    probe = probe_media(output_path, settings)
    return RenderResult(
        video_path=output_path,
        duration=probe.get("duration", round(sum(s.duration for s in scenes), 3)),
        width=probe.get("width", settings.video_width),
        height=probe.get("height", settings.video_height),
        fps=probe.get("fps", float(settings.video_fps)),
        size_bytes=os.path.getsize(output_path),
        scene_count=len(scenes),
    )


def assemble_video(
    script: Script,
    images: Dict[str, str],
    chapter_audio: Sequence[ChapterAudio],
    out_dir: str,
    settings: Settings,
    output_name: str = "final_video.mp4",
) -> RenderResult:
    """Full assembly stage: timeline -> narration track -> MP4."""
    os.makedirs(out_dir, exist_ok=True)
    scenes = build_scenes(script, images, chapter_audio, settings)
    if not scenes:
        raise ValueError("no scenes to render — the script produced no visual cues")
    narration_path = os.path.join(out_dir, "narration_full.wav")
    build_narration_track(chapter_audio, narration_path, settings)
    output_path = os.path.join(out_dir, output_name)
    return render_video(scenes, narration_path, output_path, settings)


__all__ = [
    "FFmpegMissing",
    "resolve_ffmpeg",
    "resolve_ffprobe",
    "build_scenes",
    "build_narration_track",
    "probe_media",
    "render_video",
    "assemble_video",
]
