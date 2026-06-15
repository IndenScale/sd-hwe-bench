"""Kimi CLI actor."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from sd_hwe_bench.actors.base import Actor, ActorResult
from sd_hwe_bench.sandbox.parser import YamlBlockParser

logger = logging.getLogger(__name__)


class KimiActor(Actor):
    """Run Kimi CLI in one-shot prompt mode."""

    name = "kimi"

    def __init__(
        self,
        model: str | None = None,
        timeout: int = 600,
        kimi_bin: str = "kimi",
    ):
        super().__init__(model=model or "kimi-code/kimi-for-coding", timeout=timeout)
        self.kimi_bin = kimi_bin

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
            "-m", self.model,
            "--output-format", "text",
            "-p", prompt,
        ]

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

        # Kimi may write files directly; also parse any YAML blocks from output
        parser = YamlBlockParser(workspace_root)
        written, errors = parser.parse_and_write(raw)

        if errors:
            logger.debug("Kimi parse errors: %s", errors)

        # Count YAML files excluding scaffold
        yaml_files = list(workspace_root.rglob("*.yaml")) + list(workspace_root.rglob("*.yml"))

        return ActorResult(
            success=True,
            raw_output=raw,
            files_written=len(yaml_files) if not written else written,
            elapsed_s=elapsed,
        )
