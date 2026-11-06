"""CLI behaviour: failure modes, provider reporting and manifest flags."""

from __future__ import annotations

import json

from pipeline.cli import main as cli_main


def test_run_without_keys_fails_loudly_instead_of_stubbing(tmp_path, capsys):
    out_dir = tmp_path / "nokey"
    exit_code = cli_main(["run", "--topic", "Anything", "--out", str(out_dir)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "PERPLEXITY_API_KEY" in captured.err or "PERPLEXITY_API_KEY" in captured.out

    manifest = json.loads((out_dir / "run.json").read_text())
    assert manifest["status"] == "failed"
    # A run that never executed is not a deliverable.
    assert manifest["publishable"] is False
    assert "PERPLEXITY_API_KEY" in manifest["error"]
    assert not (out_dir / "final_video.mp4").exists()


def test_providers_command_reports_offline_matrix(capsys):
    assert cli_main(["providers", "--offline"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["offline"] is True
    assert payload["research"]["provider"] == "offline"
    assert payload["narration"]["provider"] == "offline-silence"


def test_providers_command_exits_nonzero_without_keys(capsys):
    assert cli_main(["providers"]) == 1
    assert "No research provider configured" in capsys.readouterr().err
