"""Provider selection: offline mode, key-based fallback and hard failure."""

from __future__ import annotations

import pytest

from pipeline.config import Settings
from pipeline.providers import (
    OfflineImageProvider,
    OfflineNarrationProvider,
    OfflineResearchProvider,
    OfflineScriptProvider,
    OpenAIResearchProvider,
    OpenAITTSNarrationProvider,
    PerplexityResearchProvider,
    ProviderUnavailable,
    ElevenLabsNarrationProvider,
    select_providers,
)


def test_offline_mode_uses_stubs_and_requires_no_keys():
    settings = Settings.from_env(offline_override=True)
    plan = select_providers(settings)

    assert plan.offline is True
    assert isinstance(plan.research, OfflineResearchProvider)
    assert isinstance(plan.script, OfflineScriptProvider)
    assert isinstance(plan.narration, OfflineNarrationProvider)
    assert isinstance(plan.images, OfflineImageProvider)
    assert any("not publishable" in note for note in plan.notes)


def test_offline_flag_wins_even_when_keys_are_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
    settings = Settings.from_env(offline_override=True)

    plan = select_providers(settings)
    assert isinstance(plan.research, OfflineResearchProvider)
    assert isinstance(plan.narration, OfflineNarrationProvider)


def test_prefers_perplexity_for_research_and_elevenlabs_for_voice(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
    settings = Settings.from_env()

    plan = select_providers(settings)
    assert isinstance(plan.research, PerplexityResearchProvider)
    assert isinstance(plan.narration, ElevenLabsNarrationProvider)
    assert plan.offline is False


def test_falls_back_to_openai_when_vendor_keys_are_missing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = Settings.from_env()

    plan = select_providers(settings)
    assert isinstance(plan.research, OpenAIResearchProvider)
    assert isinstance(plan.narration, OpenAITTSNarrationProvider)
    # The fallback must be visible in the run manifest, not silent.
    assert any("PERPLEXITY_API_KEY unset" in note for note in plan.notes)
    assert any("ELEVENLABS_API_KEY unset" in note for note in plan.notes)


def test_missing_keys_raise_instead_of_silently_using_stubs():
    settings = Settings.from_env()
    with pytest.raises(ProviderUnavailable) as excinfo:
        select_providers(settings)
    message = str(excinfo.value)
    assert "PERPLEXITY_API_KEY" in message
    assert "OPENAI_API_KEY" in message


def test_redacted_settings_never_leak_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")
    settings = Settings.from_env()
    redacted = settings.redacted()
    assert redacted["openai_api_key"] == "set"
    assert "sk-super-secret" not in str(redacted)


def test_offline_research_brief_is_labelled_and_has_no_real_urls():
    plan = select_providers(Settings.from_env(offline_override=True))
    brief = plan.research.research("Anything")
    assert brief.offline is True
    assert brief.citations, "offline brief should still exercise the citation path"
    assert all(c.placeholder for c in brief.citations)
    assert all(not c.url for c in brief.citations)
    assert "OFFLINE PLACEHOLDER" in brief.summary


def test_offline_script_produces_parseable_cues():
    plan = select_providers(Settings.from_env(offline_override=True))
    brief = plan.research.research("Anything")
    script = plan.script.write_script(brief, Settings.from_env(offline_override=True))

    assert script.chapters
    assert script.word_count > 0
    cues = script.all_cues()
    assert cues, "offline script must emit visual cues for the image stage"
    assert all(cue.text for cue in cues)
