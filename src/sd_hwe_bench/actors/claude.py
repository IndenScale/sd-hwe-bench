"""Claude Code CLI actor.

Claude Code ``--print`` mode mutates the working directory directly.  For the
AIDC v7 DeepSeek Flash rerun we configure Claude Code to use DeepSeek's
Anthropic-compatible endpoint through environment variables, while preserving
the same ActorResult semantics as the Kimi and Codex actors.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from sd_hwe_bench.actors.base import Actor, ActorResult, count_changed_yaml_files, snapshot_yaml_files
from sd_hwe_bench.settings import settings


def _read_zshrc_var(name: str) -> str | None:
    """Best-effort read of a variable exported from ~/.zshrc without logging it."""
    zsh = shutil.which("zsh")
    if zsh is None:
        return None
    try:
        result = subprocess.run(
            [zsh, "-ic", f'printf "%s" "${{{name}:-}}"'],
            text=True,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        return None
    value = result.stdout.strip()
    return value or None


def _deepseek_auth_token(env: dict[str, str]) -> str | None:
    if env.get("ANTHROPIC_AUTH_TOKEN"):
        return env["ANTHROPIC_AUTH_TOKEN"]
    if env.get("ANTHROPIC_API_KEY"):
        return env["ANTHROPIC_API_KEY"]
    if env.get("DEEPSEEK_API_KEY"):
        return env["DEEPSEEK_API_KEY"]
    return _read_zshrc_var("DEEPSEEK_API_KEY")


def build_claude_env(model: str) -> dict[str, str]:
    """Build the Claude Code environment for DeepSeek's Anthropic endpoint."""
    env = os.environ.copy()
    env.setdefault("ANTHROPIC_BASE_URL", settings.CLAUDE_BASE_URL)
    env.setdefault("ANTHROPIC_MODEL", model)
    env.setdefault("ANTHROPIC_DEFAULT_OPUS_MODEL", settings.CLAUDE_DEFAULT_OPUS_MODEL)
    env.setdefault("ANTHROPIC_DEFAULT_SONNET_MODEL", settings.CLAUDE_DEFAULT_SONNET_MODEL)
    env.setdefault("ANTHROPIC_DEFAULT_HAIKU_MODEL", settings.CLAUDE_DEFAULT_HAIKU_MODEL)
    env.setdefault("CLAUDE_CODE_SUBAGENT_MODEL", settings.CLAUDE_DEFAULT_HAIKU_MODEL)
    env.setdefault("CLAUDE_CODE_EFFORT_LEVEL", settings.CLAUDE_EFFORT_LEVEL)

    token = _deepseek_auth_token(env)
    if token:
        env.setdefault("ANTHROPIC_AUTH_TOKEN", token)
    return env


class ClaudeActor(Actor):
    """Run Claude Code in print mode and inspect files it changed."""

    name = "claude"

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        claude_bin: str | None = None,
    ):
        super().__init__(model=model or settings.DEFAULT_CLAUDE_MODEL, timeout=timeout)
        self.claude_bin = claude_bin if claude_bin is not None else settings.CLAUDE_BIN

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        workspace_root = Path(workspace_root).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.claude_bin) is None:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=f"Claude Code CLI not found: {self.claude_bin}",
            )

        cmd = [
            self.claude_bin,
            "--print",
            "--output-format",
            "text",
            "--model",
            self.model,
            "--effort",
            settings.CLAUDE_EFFORT_LEVEL,
            *settings.CLAUDE_EXTRA_ARGS,
            prompt,
        ]

        before = snapshot_yaml_files(workspace_root)
        env = build_claude_env(self.model)

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=str(workspace_root),
                env=env,
            )
            elapsed = time.time() - start
            raw = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            return ActorResult(
                success=False,
                raw_output="[TIMEOUT]",
                files_written=0,
                elapsed_s=elapsed,
                error=f"Timeout after {self.timeout}s",
            )
        except Exception as exc:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=str(exc),
            )

        files_changed = count_changed_yaml_files(before, workspace_root)
        error = None
        success = True
        if result.returncode != 0:
            success = False
            error = f"Claude Code CLI exited with code {result.returncode}"
        elif "auth.login_required" in raw or "OAuth provider credentials were rejected" in raw:
            success = False
            error = "Claude Code authentication failed"
        elif "invalid x-api-key" in raw.lower() or "authentication_error" in raw.lower():
            success = False
            error = "Claude Code authentication failed"
        elif "model is not supported" in raw.lower() or "unsupported model" in raw.lower():
            success = False
            error = "Claude Code model is not supported"

        return ActorResult(
            success=success,
            raw_output=raw,
            files_written=files_changed,
            elapsed_s=elapsed,
            error=error,
        )
