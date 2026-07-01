"""Kimi CLI actor.

Kimi Code runs in headless one-shot prompt mode (``kimi -p ...``).  In this
mode it executes non-interactively and prints its response; it does **not**
combine with ``-y/--yolo`` (``kimi`` rejects that with "Cannot combine
--prompt with --yolo").  Tool-call approval and process-exit behavior therefore
depend on the Kimi CLI's own configuration (``config.toml``), not on a flag we
pass here.  The stdout/stderr transcript is kept for traceability, but the
authoritative agent submission is the set of new YAML files it created on disk.

The actor command is wrapped with macOS seatbelt (``sandbox-exec``) when actor
isolation places the workspace outside the benchmark repo, so the agent cannot
read reference solutions via shell tools.  See ``actors.sandbox_exec``.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from sd_hwe_bench.actors.base import (
    Actor,
    ActorResult,
    count_changed_yaml_files,
    snapshot_yaml_files,
    to_text,
)
from sd_hwe_bench.actors.sandbox_exec import maybe_wrap
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

    def _capture(self, cmd: list[str], cwd: Path) -> tuple[int, str, str, bool]:
        """Run ``cmd`` streaming output to buffers; return (rc, stdout, stderr, timed_out).

        Uses ``Popen`` + ``communicate`` so that on timeout we still recover the
        output produced so far (decoded via :func:`to_text`).  The child is
        started in its own session so we can kill the whole process group —
        ``kimi`` spawns a Node runtime that would otherwise be orphaned.
        """
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            out, err = proc.communicate(timeout=self.timeout)
            return proc.returncode, to_text(out), to_text(err), False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            try:
                out, err = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                out, err = "", ""
            return proc.returncode, to_text(out), to_text(err), True

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
        cmd = maybe_wrap(cmd, workspace_root, settings.ACTOR_SANDBOX)

        before = snapshot_yaml_files(workspace_root)

        start = time.time()
        try:
            returncode, stdout, stderr, timed_out = self._capture(cmd, workspace_root)
        except Exception as exc:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=time.time() - start,
                error=str(exc),
            )
        elapsed = time.time() - start
        files_changed = count_changed_yaml_files(before, workspace_root)

        if timed_out:
            raw = "[TIMEOUT]\n" + stdout + "\n" + stderr
            return ActorResult(
                success=False,
                raw_output=raw,
                files_written=files_changed,
                elapsed_s=elapsed,
                error=f"Timeout after {self.timeout}s",
            )

        raw = stdout + "\n" + stderr
        error = None
        success = True
        if returncode != 0:
            success = False
            error = f"Kimi CLI exited with code {returncode}"
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
