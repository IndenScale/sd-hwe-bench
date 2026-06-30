"""Kimi CLI actor.

Kimi Code runs in headless one-shot prompt mode (``kimi -p ...``).  In this
mode Kimi auto-approves tool calls and mutates the working directory directly.
The stdout/stderr transcript is kept for traceability, but the authoritative
agent submission is the set of new YAML files it created on disk.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from sd_hwe_bench.actors.base import Actor, ActorResult, count_changed_yaml_files, snapshot_yaml_files
from sd_hwe_bench.settings import settings

logger = logging.getLogger(__name__)


class KimiActor(Actor):
    """Run Kimi CLI in one-shot prompt mode and inspect files it created."""

    name = "kimi"

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        kimi_bin: str | None = None,
    ):
        super().__init__(model=model or settings.DEFAULT_KIMI_MODEL, timeout=timeout)
        self.kimi_bin = kimi_bin if kimi_bin is not None else settings.KIMI_BIN

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        workspace_root = Path(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.kimi_bin) is None:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=f"Kimi CLI not found: {self.kimi_bin}",
            )

        cmd = [
            self.kimi_bin,
            "-m",
            self.model,
            "--output-format",
            "text",
            "-p",
            prompt,
        ]

        before = snapshot_yaml_files(workspace_root)

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
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - start
            files_changed = count_changed_yaml_files(before, workspace_root)
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            raw = "[TIMEOUT]\n" + stdout + "\n" + stderr
            return ActorResult(
                success=False,
                raw_output=raw,
                files_written=files_changed,
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
            error = f"Kimi CLI exited with code {result.returncode}"
        elif "auth.login_required" in raw or "OAuth provider credentials were rejected" in raw:
            success = False
            error = "Kimi CLI authentication failed"

        return ActorResult(
            success=success,
            raw_output=raw,
            files_written=files_changed,
            elapsed_s=elapsed,
            error=error,
        )
