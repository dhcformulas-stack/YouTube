"""Assembly: scene timing, and a real offline render that ffprobe can read."""

from __future__ import annotations

import json

import pytest

from pipeline.assembly import (
    FFmpegMissing,
    assemble_video,
    build_scenes,
    probe_media,
    resolve_ffmpeg,
)
from pipeline.cli import main as cli_main
from pipeline.models import Chapter, ChapterAudio, Script, VisualCue


def _script_with_cues() -> Script:
    chapter = Chapter(
        index=1,
        title="Origins",
        narration="First sentence about 1901. Second sentence.",
        cues=[
            VisualCue(id="c1", chapter_index=1, order=1, text="shot one", narrator_words=30),
            VisualCue(id="c2", chapter_index=1, order=2, text="shot two", narrator_words=10),
        ],
    )
    return Script(topic="T", title="T", chapters=[chapter])


def test_scene_durations_split_chapter_audio_by_word_count():
    from pipeline.config import Settings

    settings = Settings.from_env(offline_override=True)
    settings.min_scene_seconds = 1.0
    script = _script_with_cues()
    images = {cue.id: __file__ for cue in script.all_cues()}
    tracks = [ChapterAudio(chapter_index=1, path="", duration=41.0)]

    scenes = build_scenes(script, images, tracks, settings)

    assert len(scenes) == 2
    total = sum(s.duration for s in scenes)
    assert total == pytest.approx(41.0, abs=0.1)
    # Cue 1 carries 30 of the 40 narrator words, so it must stay up far longer.
    assert scenes[0].duration > scenes[1].duration
    assert scenes[0].duration == pytest.approx(1.0 + (41.0 - 2.0) * (30 / 40), abs=0.2)


def test_scenes_skip_images_that_failed_to_generate():
    from pipeline.config import Settings

    settings = Settings.from_env(offline_override=True)
    script = _script_with_cues()
    images = {cue.id: __file__ for cue in script.all_cues() if cue.id == "c1"}
    scenes = build_scenes(script, images, [ChapterAudio(1, "", 12.0)], settings)
    assert [s.image_path for s in scenes] == [__file__]


def test_assembly_requires_ffmpeg_binary(monkeypatch):
    from pipeline.config import Settings

    settings = Settings.from_env(offline_override=True)
    monkeypatch.setenv("FFMPEG_BIN", "/nonexistent/ffmpeg")
    with pytest.raises(FFmpegMissing):
        resolve_ffmpeg(settings)


@pytest.fixture
def require_ffmpeg():
    try:
        resolve_ffmpeg()
    except FFmpegMissing as exc:  # pragma: no cover - environment dependent
        pytest.skip(str(exc))


def test_offline_run_produces_a_playable_mp4(tmp_path, require_ffmpeg):
    out_dir = tmp_path / "proof"
    exit_code = cli_main(
        [
            "run",
            "--topic",
            "The Antikythera Mechanism",
            "--out",
            str(out_dir),
            "--offline",
            "--minutes",
            "0.5",
            "--chapters",
            "2",
            "--width",
            "640",
            "--height",
            "360",
            "--fps",
            "10",
        ]
    )
    assert exit_code == 0, "offline pipeline should complete without keys"

    video = out_dir / "final_video.mp4"
    assert video.exists() and video.stat().st_size > 10_000

    info = probe_media(str(video))
    assert info["width"] == 640
    assert info["height"] == 360
    assert info["duration"] > 20  # half a minute of narration plus tolerance
    assert info["fps"] == pytest.approx(10, abs=0.1)

    manifest = json.loads((out_dir / "run.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["offline"] is True
    assert manifest["publishable"] is False
    assert manifest["stages"]["factcheck"]["passed"] is True
    assert manifest["stages"]["assembly"]["scenes"] > 1
    assert manifest["settings"]["openai_api_key"] == "unset"
    # Every stage artifact is listed in the manifest for the backend to pick up.
    for stage in ("research", "script", "factcheck", "narration", "images", "assembly"):
        assert stage in manifest["stages"]


def test_assemble_video_rejects_an_empty_timeline(tmp_path):
    from pipeline.config import Settings

    settings = Settings.from_env(offline_override=True)
    script = Script(topic="T", chapters=[])
    with pytest.raises(ValueError):
        assemble_video(script, {}, [], str(tmp_path), settings)
