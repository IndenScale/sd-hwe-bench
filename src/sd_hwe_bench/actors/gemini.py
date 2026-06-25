"""Gemini CLI actor.

Gemini's ``--yolo`` mode mutates the working directory directly.  We keep the
stdout/stderr transcript for traceability but score the files it actually
wrote to disk.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from sd_hwe_bench.actors.base import Actor, ActorResult, list_yaml_files
from sd_hwe_bench.settings import settings

logger = logging.getLogger(__name__)


class GeminiActor(Actor):
    """Run Google Gemini CLI in one-shot prompt mode and inspect files it created."""

    name = "gemini"

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        gemini_bin: str | None = None,
    ):
        super().__init__(model=model or settings.DEFAULT_GEMINI_MODEL, timeout=timeout)
        self.gemini_bin = gemini_bin if gemini_bin is not None else settings.GEMINI_BIN

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        workspace_root = Path(workspace_root).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.gemini_bin) is None:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=f"Gemini CLI not found: {self.gemini_bin}",
            )

        # Gemini CLI requires a git repo for tool access
        git_dir = workspace_root / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init", "-q"],
                    cwd=str(workspace_root),
                    capture_output=True,
                    timeout=settings.GEMINI_GIT_TIMEOUT_S,
                )
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(workspace_root),
                    capture_output=True,
                    timeout=settings.GEMINI_GIT_TIMEOUT_S,
                )
                subprocess.run(
                    ["git", "commit", "-m", "scaffold", "--allow-empty", "-q"],
                    cwd=str(workspace_root),
                    capture_output=True,
                    timeout=settings.GEMINI_GIT_TIMEOUT_S,
                )
            except Exception:
                logger.warning("Failed to init git repo for Gemini")

        cmd = [
            self.gemini_bin,
            "--prompt",
            prompt,
            "--model",
            self.model,
            "--yolo",
            "--skip-trust",
            "--output-format",
            "text",
        ]

        before = list_yaml_files(workspace_root)

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=str(workspace_root),
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

        after = list_yaml_files(workspace_root)
        new_files = after - before

        return ActorResult(
            success=True,
            raw_output=raw,
            files_written=len(new_files),
            elapsed_s=elapsed,
        )
