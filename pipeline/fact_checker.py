"""Stage 3 — fact checking.

Every factual sentence in the script must trace to a citation in the research
brief. This stage is deterministic (no LLM), so its verdict is reproducible and
cheap enough to run on every video:

* a sentence carrying ``[S3]`` is **supported** when ``S3`` exists in the brief;
* a factual sentence with no marker is **unsupported** ("no citation");
* a marker pointing at a source that is not in the brief is **unsupported**
  ("unknown source") — that is how a fabricated source gets caught;
* a resolved source with no URL is downgraded to **review** and listed in
  ``invalid_citations``, because a claim we cannot point at is not verified.

The report is written as JSON (for the backend / admin dashboard) and markdown
(for the human reviewer).
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from .models import ClaimCheck, FactCheckReport, ResearchBrief, Script, dump_json
from .script_parser import extract_citation_ids, strip_citation_markers

# Split on sentence end, also when the next sentence opens with a citation
# marker such as "[S2]".
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“\[])")

# Patterns that make a sentence a checkable factual claim even without a marker.
FACTUAL_PATTERNS = [
    re.compile(r"\b(1\d{3}|20\d{2})\b"),                      # a year
    re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|percent)\b", re.I),    # percentages
    re.compile(
        r"\b(first|oldest|earliest|largest|smallest|invented|founded|discovered|"
        r"born|died|published|built|launched|patented|signed|declared)\b",
        re.I,
    ),
    re.compile(r"\b\d[\d,\.]*\s?(?:km|kg|miles|metres|meters|tons|tonnes|years|BCE|CE|AD)\b", re.I),
]


def split_sentences(text: str) -> List[str]:
    sentences: List[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        if not block:
            continue
        for sentence in SENTENCE_SPLIT_RE.split(block):
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
    return sentences


def looks_factual(sentence: str) -> bool:
    return any(pattern.search(sentence) for pattern in FACTUAL_PATTERNS)


def check_script(script: Script, brief: ResearchBrief) -> FactCheckReport:
    """Compare the script against the research brief."""
    citation_map: Dict[str, object] = brief.citation_map()
    report = FactCheckReport()
    invalid: List[str] = []

    for chapter in script.chapters:
        for sentence in split_sentences(chapter.narration):
            ids = extract_citation_ids(sentence)
            factual = looks_factual(sentence)
            if not ids and not factual:
                continue

            report.total_claims += 1
            claim_text = strip_citation_markers(sentence)
            check = ClaimCheck(
                chapter_index=chapter.index,
                claim=claim_text,
                citation_ids=ids,
            )

            if not ids:
                check.status = "unsupported"
                check.reason = "factual sentence carries no citation marker"
            else:
                unknown = [cid for cid in ids if cid not in citation_map]
                if unknown:
                    check.status = "unsupported"
                    check.reason = "citation marker(s) not present in research brief: " + ", ".join(unknown)
                    for cid in unknown:
                        if cid not in invalid:
                            invalid.append(cid)
                else:
                    cited = [citation_map[cid] for cid in ids]
                    placeholders = [c for c in cited if getattr(c, "placeholder", False)]
                    missing_url = [
                        c for c in cited
                        if not getattr(c, "placeholder", False) and not (getattr(c, "url", "") or "").strip()
                    ]
                    if placeholders:
                        report.offline_placeholders += 1
                        check.status = "review"
                        check.reason = "offline placeholder source — nothing was actually verified"
                    elif missing_url:
                        check.status = "review"
                        check.reason = "cited source has no URL and cannot be verified"
                        for c in missing_url:
                            if c.id not in invalid:
                                invalid.append(c.id)
                    else:
                        check.status = "supported"
                        check.reason = ""

            if check.status == "supported":
                report.supported += 1
            else:
                report.flagged += 1
            report.claims.append(check)

    report.invalid_citations = invalid
    report.passed = all(c.status != "unsupported" for c in report.claims)
    return report


def report_to_markdown(report: FactCheckReport, topic: str = "") -> str:
    flagged = [c for c in report.claims if c.status != "supported"]
    lines = [f"# Fact-Check Report{' — ' + topic if topic else ''}", ""]
    lines += [
        f"- Claims checked: **{report.total_claims}**",
        f"- Supported: **{report.supported}**",
        f"- Flagged: **{report.flagged}**",
        f"- Verdict: **{'PASS' if report.passed else 'FAIL'}**",
        "",
    ]
    if report.offline_placeholders:
        lines += [
            f"> {report.offline_placeholders} claim(s) rest on offline placeholder "
            "sources. This report is a pipeline smoke test, not an accuracy review.",
            "",
        ]
    if report.invalid_citations:
        lines += [
            "## Invalid or unverifiable sources",
            "",
            *[f"- `{cid}`" for cid in report.invalid_citations],
            "",
        ]
    if flagged:
        lines += ["## Flagged claims", ""]
        for check in flagged:
            lines.append(f"- **Chapter {check.chapter_index} — {check.status}**: {check.claim}")
            lines.append(f"  - {check.reason}")
        lines.append("")
    else:
        lines += ["No flagged claims.", ""]
    return "\n".join(lines).rstrip() + "\n"


def run_fact_check(
    script: Script,
    brief: ResearchBrief,
    out_dir: str,
) -> Tuple[FactCheckReport, str]:
    """Run the fact-check stage and write the report files."""
    os.makedirs(out_dir, exist_ok=True)
    report = check_script(script, brief)
    json_path = os.path.join(out_dir, "factcheck_report.json")
    payload = report.to_dict()
    payload["topic"] = script.topic
    dump_json(payload, json_path)
    with open(os.path.join(out_dir, "factcheck_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report_to_markdown(report, script.topic))
    return report, json_path


def verify_claims(script_file: str, research_file: str) -> bool:
    """Legacy helper kept for callers of the old placeholder API."""
    from .models import load_json
    from .script_parser import script_from_markdown_file

    script = script_from_markdown_file(script_file)
    brief_data = load_json(research_file)
    from .models import Citation, Fact, ResearchBrief

    brief = ResearchBrief(
        topic=brief_data.get("topic", ""),
        summary=brief_data.get("summary", ""),
        facts=[Fact(**f) for f in brief_data.get("facts", [])],
        timeline=brief_data.get("timeline", []),
        citations=[Citation(**c) for c in brief_data.get("citations", [])],
        provider=brief_data.get("provider", ""),
        model=brief_data.get("model", ""),
        offline=brief_data.get("offline", False),
    )
    return check_script(script, brief).passed


__all__ = [
    "split_sentences",
    "looks_factual",
    "check_script",
    "report_to_markdown",
    "run_fact_check",
    "verify_claims",
]
