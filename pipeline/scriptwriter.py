"""Stage 2 — scriptwriting.

Turns the research brief into a chaptered documentary script and reports how far
the delivered word count is from the requested runtime.
"""

from __future__ import annotations

import os
from typing import Tuple

from .config import Settings
from .models import ResearchBrief, Script, dump_json
from .providers import ProviderPlan


def runtime_report(script: Script, target_minutes: float) -> dict:
    target_words = int(round(target_minutes * script.words_per_minute))
    actual = script.word_count
    delta_pct = 0.0 if not target_words else round((actual - target_words) / target_words * 100, 1)
    return {
        "target_minutes": target_minutes,
        "target_words": target_words,
        "word_count": actual,
        "estimated_minutes": script.estimated_minutes,
        "delta_percent": delta_pct,
        "on_target": abs(delta_pct) <= 15.0,
    }


def run_script(
    brief: ResearchBrief,
    settings: Settings,
    plan: ProviderPlan,
    out_dir: str,
) -> Tuple[Script, str]:
    """Run the scriptwriting stage. Returns the script and the markdown path."""
    os.makedirs(out_dir, exist_ok=True)
    script = plan.script.write_script(brief, settings)
    md_path = os.path.join(out_dir, "script.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(script.to_markdown())
    payload = script.to_dict()
    payload["runtime"] = runtime_report(script, settings.target_minutes)
    dump_json(payload, os.path.join(out_dir, "script.json"))
    return script, md_path


__all__ = ["run_script", "runtime_report"]
