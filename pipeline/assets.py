"""Stage 5 — visual assets (one still per ``[VISUAL: ...]`` cue).

Images are generated in cue order and written to ``<out>/images``. The manifest
records the exact prompt used per cue, which is what a reviewer needs to
regenerate a single shot.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from .config import Settings
from .models import Script, dump_json
from .providers import ProviderPlan


def generate_assets(
    script: Script,
    settings: Settings,
    plan: ProviderPlan,
    out_dir: str,
) -> Tuple[Dict[str, str], str]:
    """Generate an image for every cue. Returns ``{cue_id: path}`` + manifest."""
    image_dir = os.path.join(out_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    mapping: Dict[str, str] = {}
    records: List[dict] = []

    for chapter in script.chapters:
        for cue in chapter.cues:
            filename = f"ch{chapter.index:02d}_{cue.order:03d}.png"
            path = os.path.join(image_dir, filename)
            plan.images.generate(
                cue.image_prompt or cue.text,
                path,
                chapter_title=f"{chapter.index}. {chapter.title}",
                scene_index=len(records) + 1,
            )
            mapping[cue.id] = path
            records.append(
                {
                    "cue_id": cue.id,
                    "chapter_index": chapter.index,
                    "order": cue.order,
                    "text": cue.text,
                    "prompt": cue.image_prompt or cue.text,
                    "path": path,
                }
            )

    manifest_path = os.path.join(out_dir, "assets.json")
    dump_json(
        {
            "provider": plan.images.name,
            "model": getattr(plan.images, "model", ""),
            "count": len(records),
            "images": records,
        },
        manifest_path,
    )
    return mapping, manifest_path


__all__ = ["generate_assets"]
