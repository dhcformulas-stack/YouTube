"""Script parsing: chapter structure, [VISUAL: ...] cues, citation markers."""

from __future__ import annotations

from pipeline.script_parser import (
    build_script,
    count_words,
    extract_citation_ids,
    parse_chapter,
    parse_script_markdown,
    strip_citation_markers,
)

CHAPTER_MD = """
[VISUAL: A wide shot of a corroded bronze gear, lit from the left]
The Antikythera Mechanism was recovered in 1901 [S1]. It is the oldest known
analogue computer [S1, S2].

[VISUAL: Close-up of the front dial with Greek inscriptions]
Nothing about it is simple. The gearing models the moon's motion [S2].
"""


def test_visual_cues_are_extracted_in_order():
    chapter = parse_chapter(CHAPTER_MD, 1, "Origins")
    assert [c.text for c in chapter.cues] == [
        "A wide shot of a corroded bronze gear, lit from the left",
        "Close-up of the front dial with Greek inscriptions",
    ]
    assert [c.order for c in chapter.cues] == [1, 2]
    assert all(c.id.startswith("ch01_cue") for c in chapter.cues)


def test_cue_text_is_promptable():
    chapter = parse_chapter(CHAPTER_MD, 1, "Origins")
    assert chapter.cues[0].image_prompt == chapter.cues[0].text


def test_cue_words_are_attributed_to_the_preceding_cue():
    chapter = parse_chapter(CHAPTER_MD, 1, "Origins")
    first, second = chapter.cues
    # 16 words sit under cue 1, 11 under cue 2 — this drives scene durations.
    assert first.narrator_words > second.narrator_words > 0
    assert first.narrator_words == 14


def test_cue_markers_are_not_spoken():
    chapter = parse_chapter(CHAPTER_MD, 1, "Origins")
    assert "[VISUAL" not in chapter.narration
    assert "bronze gear" not in chapter.narration
    assert "recovered in 1901" in chapter.narration


def test_citation_markers_are_parsed_and_stripped():
    assert extract_citation_ids("The gear was bronze [S1] and small [S2][S4].") == ["S1", "S2", "S4"]
    assert extract_citation_ids("Combined form [S1, S3].") == ["S1", "S3"]
    assert extract_citation_ids("No markers here.") == []
    assert strip_citation_markers("It was bronze [S1].") == "It was bronze."


def test_word_count_ignores_markers_and_cues():
    chapter = parse_chapter(CHAPTER_MD, 1, "Origins")
    assert count_words(chapter.narration) == chapter.word_count


def test_single_visual_cue_variant_is_accepted():
    md = "[Visual: a single establishing shot]\nOne line of narration."
    chapter = parse_chapter(md, 3, "Hook")
    assert len(chapter.cues) == 1
    assert chapter.cues[0].text == "a single establishing shot"


def test_chapter_without_cues_gets_a_fallback_shot():
    chapter = parse_chapter("Just narration with no cue.", 2, "Interlude")
    assert len(chapter.cues) == 1
    assert "Interlude" in chapter.cues[0].text


def test_full_script_markdown_round_trip():
    markdown = """# My Documentary

## Chapter 1: Origins
[VISUAL: opening shot]
The first prototype ran in 1888 [S1].

## Chapter 2: Legacy
[VISUAL: closing shot]
It still shapes engineering today [S2].
"""
    script = parse_script_markdown(markdown, "My Documentary")
    assert len(script.chapters) == 2
    assert script.chapters[0].title == "Origins"
    assert script.chapters[1].index == 2
    assert len(script.all_cues()) == 2
    # Re-emitting the script keeps the cues and markers intact.
    round_tripped = parse_script_markdown(script.to_markdown(), script.topic)
    assert [c.title for c in round_tripped.chapters] == ["Origins", "Legacy"]


def test_build_script_computes_totals(sample_brief):
    script = build_script(
        topic=sample_brief.topic,
        titles=["Origins", "Legacy"],
        chapter_markdown=[
            "[VISUAL: a]\nThe mechanism is bronze [S1].",
            "[VISUAL: b]\nIt models the moon [S2].",
        ],
        provider="test",
        model="test-model",
    )
    assert script.word_count == 8
    assert script.estimated_minutes == round(8 / 140, 2)
    assert script.chapters[0].cues[0].text == "a"
