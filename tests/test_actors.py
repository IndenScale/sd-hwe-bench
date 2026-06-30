"""Tests for actor factory and base behavior."""

import subprocess

import pytest

from sd_hwe_bench.actors import (
    ClaudeActor,
    CodexActor,
    KimiActor,
    create_actor,
)
from sd_hwe_bench.actors.claude import build_claude_env
from sd_hwe_bench.actors.base import count_changed_yaml_files, snapshot_yaml_files


class TestActorFactory:
    def test_create_kimi(self):
        actor = create_actor("kimi")
        assert isinstance(actor, KimiActor)
        assert actor.model == "kimi-code/kimi-for-coding"

    def test_create_kimi_with_model(self):
        actor = create_actor("kimi:kimi-code/other")
        assert isinstance(actor, KimiActor)
        assert actor.model == "kimi-code/other"

    def test_create_codex(self):
        actor = create_actor("codex")
        assert isinstance(actor, CodexActor)
        assert actor.model == "deepseek-chat"

    def test_create_claude(self):
        actor = create_actor("claude")
        assert isinstance(actor, ClaudeActor)
        assert actor.model == "deepseek-v4-flash"

    def test_create_claude_with_model(self):
        actor = create_actor("claude:deepseek-v4-pro[1m]")
        assert isinstance(actor, ClaudeActor)
        assert actor.model == "deepseek-v4-pro[1m]"

    def test_unknown_driver(self):
        with pytest.raises(ValueError):
            create_actor("unknown")


def test_yaml_snapshot_counts_modified_files(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("id: A\n", encoding="utf-8")
    before = snapshot_yaml_files(tmp_path)

    path.write_text("id: B\n", encoding="utf-8")

    assert count_changed_yaml_files(before, tmp_path) == 1


def test_codex_actor_reports_nonzero_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("sd_hwe_bench.actors.codex.shutil.which", lambda _: "/bin/codex")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=7, stdout="", stderr="boom")

    monkeypatch.setattr("sd_hwe_bench.actors.codex.subprocess.run", fake_run)
    result = CodexActor(codex_bin="codex").run("prompt", tmp_path)

    assert not result.success
    assert result.error == "Codex CLI exited with code 7"


def test_kimi_actor_reports_auth_failure(monkeypatch, tmp_path):
    monkeypatch.setattr("sd_hwe_bench.actors.kimi.shutil.which", lambda _: "/bin/kimi")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="auth.login_required: OAuth provider credentials were rejected",
            stderr="",
        )

    monkeypatch.setattr("sd_hwe_bench.actors.kimi.subprocess.run", fake_run)
    result = KimiActor(kimi_bin="kimi").run("prompt", tmp_path)

    assert not result.success
    assert result.error == "Kimi CLI authentication failed"


def test_claude_actor_reports_nonzero_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("sd_hwe_bench.actors.claude.shutil.which", lambda _: "/bin/claude")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=2, stdout="", stderr="bad")

    monkeypatch.setattr("sd_hwe_bench.actors.claude.subprocess.run", fake_run)
    result = ClaudeActor(claude_bin="claude").run("prompt", tmp_path)

    assert not result.success
    assert result.error == "Claude Code CLI exited with code 2"


def test_claude_env_maps_deepseek_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    env = build_claude_env("deepseek-v4-flash")

    assert env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "secret"
    assert env["ANTHROPIC_MODEL"] == "deepseek-v4-flash"
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "deepseek-v4-flash"
    assert env["CLAUDE_CODE_SUBAGENT_MODEL"] == "deepseek-v4-flash"
    assert env["CLAUDE_CODE_EFFORT_LEVEL"] == "max"
