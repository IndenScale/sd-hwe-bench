"""Codex CLI actor.

Codex ``exec`` mode mutates the working directory directly.  We keep the
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


class CodexActor(Actor):
    """Run OpenAI Codex CLI in exec mode and inspect files it created."""

    name = "codex"

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        codex_bin: str | None = None,
    ):
        super().__init__(model=model or settings.DEFAULT_CODEX_MODEL, timeout=timeout)
        self.codex_bin = codex_bin if codex_bin is not None else settings.CODEX_BIN

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        workspace_root = Path(workspace_root).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.codex_bin) is None:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=f"Codex CLI not found: {self.codex_bin}",
            )

        cmd = [
            self.codex_bin,
            "exec",
            "-C",
            str(workspace_root),
            "-m",
            self.model,
            *settings.CODEX_EXTRA_ARGS,
        ]

        before = list_yaml_files(workspace_root)

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
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
