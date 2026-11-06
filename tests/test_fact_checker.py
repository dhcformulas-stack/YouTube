"""Fact checking: cited claims pass, uncited or unknown sources are flagged."""

from __future__ import annotations

from pipeline.fact_checker import check_script, report_to_markdown, split_sentences
from pipeline.models import Chapter, Citation, ResearchBrief, Script


def make_script(*bodies: str) -> Script:
    return Script(
        topic="Test topic",
        title="Test topic",
        chapters=[
            Chapter(index=i, title=f"Chapter {i}", narration=body)
            for i, body in enumerate(bodies, start=1)
        ],
    )


def test_fully_cited_script_passes(sample_brief):
    script = make_script(
        "The mechanism was recovered in 1901 [S1].",
        "Its gear train models the sun and moon [S2].",
    )
    report = check_script(script, sample_brief)
    assert report.total_claims == 2
    assert report.supported == 2
    assert report.flagged == 0
    assert report.passed is True


def test_uncited_factual_claim_is_flagged(sample_brief):
    script = make_script("The mechanism was recovered in 1901.")
    report = check_script(script, sample_brief)
    assert report.total_claims == 1
    assert report.flagged == 1
    assert report.passed is False
    flagged = report.claims[0]
    assert flagged.status == "unsupported"
    assert "no citation" in flagged.reason


def test_claim_citing_a_source_that_does_not_exist_is_flagged(sample_brief):
    script = make_script("The mechanism is 2,000 years old [S9].")
    report = check_script(script, sample_brief)
    assert report.flagged == 1
    assert report.claims[0].status == "unsupported"
    assert "S9" in report.claims[0].reason
    assert "S9" in report.invalid_citations
    assert report.passed is False


def test_citation_without_url_is_downgraded_to_review(sample_brief):
    sample_brief.citations.append(Citation(id="S3", title="No URL source", url=""))
    script = make_script("A claim supported by a sourceless citation [S3].")
    report = check_script(script, sample_brief)
    assert report.claims[0].status == "review"
    assert "S3" in report.invalid_citations
    # Review-level items do not block delivery, unsupported ones do.
    assert report.passed is True
    assert report.flagged == 1


def test_non_factual_prose_is_not_treated_as_a_claim(sample_brief):
    script = make_script("Imagine standing in the dark. The room is quiet.")
    report = check_script(script, sample_brief)
    assert report.total_claims == 0
    assert report.passed is True


def test_offline_placeholders_are_reported_not_hidden():
    brief = ResearchBrief(
        topic="T",
        citations=[Citation(id="S1", title="PLACEHOLDER", url="", placeholder=True)],
        offline=True,
    )
    script = make_script("A placeholder claim from 1901 [S1].")
    report = check_script(script, brief)
    assert report.offline_placeholders == 1
    assert report.claims[0].status == "review"
    markdown = report_to_markdown(report, "T")
    assert "offline placeholder" in markdown.lower()


def test_flagged_claims_appear_in_the_markdown_report(sample_brief):
    script = make_script("The mechanism was recovered in 1901.")
    markdown = report_to_markdown(check_script(script, sample_brief), "Test topic")
    assert "Verdict: **FAIL**" in markdown
    assert "recovered in 1901" in markdown


def test_sentence_split_handles_leading_citation_markers():
    sentences = split_sentences("It was bronze [S1]. [S2] It was small.")
    assert len(sentences) == 2
