"""Command line entry point.

    python -m pipeline.cli run --topic "The Antikythera Mechanism" --out /tmp/proof --offline

``run`` executes the full chain — research -> script -> fact-check -> narration ->
images -> assembly — and writes a JSON manifest describing exactly what ran, with
which provider, and what it produced. Without ``--offline`` the same command uses
the live providers configured through environment variables.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .assembly import FFmpegMissing, assemble_video
from .assets import generate_assets
from .config import Settings
from .fact_checker import run_fact_check
from .models import dump_json
from .narration import run_narration
from .providers import ProviderUnavailable, select_providers
from .research import run_research
from .scriptwriter import run_script


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(message: str) -> None:
    print(f"[pipeline] {message}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.cli",
        description="Chronicle Forge documentary video pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the full pipeline for one topic")
    run.add_argument("--topic", required=True, help="documentary subject")
    run.add_argument("--out", required=True, help="output directory (use /tmp on small disks)")
    run.add_argument(
        "--offline",
        action="store_true",
        help="use deterministic stub providers; needs no API keys (implies not publishable)",
    )
    run.add_argument("--criteria", default="", help="extra audience/style constraints")
    run.add_argument("--minutes", type=float, default=None, help="target runtime (default 30)")
    run.add_argument("--chapters", type=int, default=None, help="chapter count (default 8)")
    run.add_argument("--width", type=int, default=None, help="output width (default 1920)")
    run.add_argument("--height", type=int, default=None, help="output height (default 1080)")
    run.add_argument("--fps", type=int, default=None, help="output fps (default 30)")
    run.add_argument(
        "--allow-factcheck-failures",
        action="store_true",
        help="keep going even if the fact-check stage flags unsupported claims",
    )
    run.add_argument(
        "--skip-video",
        action="store_true",
        help="stop after images (useful when ffmpeg is unavailable)",
    )

    providers = sub.add_parser("providers", help="print which provider each stage will use")
    providers.add_argument("--offline", action="store_true", help="resolve providers in offline mode")

    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env(offline_override=True if getattr(args, "offline", False) else None)
    if getattr(args, "minutes", None):
        settings.target_minutes = args.minutes
    if getattr(args, "chapters", None):
        settings.chapters = args.chapters
    if getattr(args, "width", None):
        settings.video_width = args.width
    if getattr(args, "height", None):
        settings.video_height = args.height
    if getattr(args, "fps", None):
        settings.video_fps = args.fps
    return settings


def cmd_providers(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    try:
        plan = select_providers(settings)
    except ProviderUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(plan.describe(), indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    settings = settings_from_args(args)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    run_id = uuid.uuid4().hex[:12]
    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "started_at": _now(),
        "topic": args.topic,
        "criteria": args.criteria,
        "offline": settings.offline,
        "publishable": not settings.offline,
        "settings": settings.redacted(),
        "stages": {},
    }
    timings: Dict[str, float] = {}
    status = "failed"
    error: Optional[str] = None

    try:
        plan = select_providers(settings)
    except ProviderUnavailable as exc:
        _log(f"ERROR: {exc}")
        manifest["error"] = str(exc)
        manifest["status"] = "failed"
        manifest["publishable"] = False
        manifest["finished_at"] = _now()
        dump_json(manifest, os.path.join(out_dir, "run.json"))
        return 2

    manifest["providers"] = plan.describe()
    for note in plan.notes:
        _log(f"note: {note}")
    _log(f"run {run_id} — topic={args.topic!r} offline={settings.offline}")

    try:
        started = time.time()
        brief, brief_path = run_research(args.topic, settings, plan, out_dir, args.criteria)
        timings["research"] = round(time.time() - started, 2)
        manifest["stages"]["research"] = {
            "provider": brief.provider,
            "model": brief.model,
            "web_search": getattr(brief, "web_search", False),
            "facts": len(brief.facts),
            "citations": len(brief.citations),
            "output": brief_path,
        }
        _log(f"research: {len(brief.facts)} facts, {len(brief.citations)} sources ({timings['research']}s)")

        started = time.time()
        script, script_path = run_script(brief, settings, plan, out_dir)
        timings["script"] = round(time.time() - started, 2)
        manifest["stages"]["script"] = {
            "provider": script.provider,
            "model": script.model,
            "chapters": len(script.chapters),
            "word_count": script.word_count,
            "estimated_minutes": script.estimated_minutes,
            "output": script_path,
        }
        _log(
            f"script: {script.word_count} words across {len(script.chapters)} chapters "
            f"(~{script.estimated_minutes} min) ({timings['script']}s)"
        )

        started = time.time()
        report, report_path = run_fact_check(script, brief, out_dir)
        timings["factcheck"] = round(time.time() - started, 2)
        manifest["stages"]["factcheck"] = {
            "passed": report.passed,
            "claims": report.total_claims,
            "supported": report.supported,
            "flagged": report.flagged,
            "invalid_citations": report.invalid_citations,
            "offline_placeholders": report.offline_placeholders,
            "output": report_path,
        }
        _log(
            f"factcheck: {report.supported}/{report.total_claims} supported, "
            f"{report.flagged} flagged -> {'PASS' if report.passed else 'FAIL'}"
        )
        if not report.passed and not args.allow_factcheck_failures:
            raise SystemExit(
                "fact-check failed: unsupported claims in the script. Review "
                f"{report_path} or re-run with --allow-factcheck-failures."
            )

        started = time.time()
        tracks, narration_path = run_narration(script, settings, plan, out_dir)
        timings["narration"] = round(time.time() - started, 2)
        total_audio = round(sum(t.duration for t in tracks), 2)
        manifest["stages"]["narration"] = {
            "provider": plan.narration.name,
            "chapters": len(tracks),
            "total_duration": total_audio,
            "characters": sum(t.characters for t in tracks),
            "output": narration_path,
        }
        _log(f"narration: {total_audio}s across {len(tracks)} files ({timings['narration']}s)")

        started = time.time()
        images, assets_path = generate_assets(script, settings, plan, out_dir)
        timings["images"] = round(time.time() - started, 2)
        manifest["stages"]["images"] = {
            "provider": plan.images.name,
            "model": getattr(plan.images, "model", ""),
            "count": len(images),
            "output": assets_path,
        }
        _log(f"images: {len(images)} generated ({timings['images']}s)")

        if args.skip_video:
            status = "completed_without_video"
            manifest["publishable"] = False
        else:
            started = time.time()
            result = assemble_video(script, images, tracks, out_dir, settings)
            timings["assembly"] = round(time.time() - started, 2)
            manifest["stages"]["assembly"] = {
                "output": result.video_path,
                "duration": result.duration,
                "width": result.width,
                "height": result.height,
                "fps": result.fps,
                "size_bytes": result.size_bytes,
                "scenes": result.scene_count,
            }
            _log(
                f"assembly: {result.video_path} — {result.duration}s, "
                f"{result.width}x{result.height}@{result.fps}, "
                f"{result.size_bytes / 1e6:.1f} MB ({timings['assembly']}s)"
            )
            status = "completed"
    except SystemExit as exc:  # fact-check gate
        error = str(exc)
        status = "blocked"
    except FFmpegMissing as exc:
        error = str(exc)
        status = "failed"
    except Exception as exc:  # noqa: BLE001 - surfaced in the manifest
        error = f"{type(exc).__name__}: {exc}"
        status = "failed"

    manifest["status"] = status
    # Only a completed, online run is deliverable: offline stubs and every
    # failure mode must be visibly non-publishable in the manifest.
    manifest["publishable"] = status == "completed" and not settings.offline
    manifest["finished_at"] = _now()
    manifest["stage_seconds"] = timings
    manifest["total_seconds"] = round(sum(timings.values()), 2)
    if error:
        manifest["error"] = error
    manifest_path = os.path.join(out_dir, "run.json")
    dump_json(manifest, manifest_path)

    if status == "failed":
        _log(f"FAILED: {error}")
        return 1
    if status == "blocked":
        _log(f"BLOCKED: {error}")
        return 3
    _log(f"done — manifest: {manifest_path}")
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "providers":
        return cmd_providers(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
