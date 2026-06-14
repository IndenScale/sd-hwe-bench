"""Codex CLI agent driver for SD-HWE-Bench."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class CodexDriver:
    """Run a single benchmark task via Codex CLI."""

    def __init__(
        self,
        model: str = "deepseek-chat",
        timeout_seconds: int = 600,
        codex_bin: str = "codex",
    ):
        self.model = model
        self.timeout = timeout_seconds
        self.codex_bin = codex_bin

    def run(
        self,
        prompt: str,
        scaffold_dir: Path,
        output_dir: Path,
    ) -> bool:
        """Run the agent on a task.

        Copies scaffold into output_dir, invokes codex exec with the prompt,
        and leaves the agent's output files in output_dir.
        """
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if scaffold_dir.exists():
            _copy_scaffold(scaffold_dir, output_dir)

        prompt_file = output_dir / ".sd-hwe-prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")

        cmd = [
            self.codex_bin, "exec",
            "-C", str(output_dir),
            "-m", self.model,
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
        ]

        try:
            logger.info(
                "Running codex: model=%s cwd=%s timeout=%ds prompt_len=%d",
                self.model, output_dir, self.timeout, len(prompt),
            )

            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=output_dir,
            )

            stderr_tail = result.stderr.strip().split("\n")[-3:]
            for line in stderr_tail:
                if line.strip():
                    logger.debug("codex: %s", line[:200])

            yaml_files = list(output_dir.rglob("*.yaml")) + list(output_dir.rglob("*.yml"))
            scaffold_yaml = (
                list(scaffold_dir.rglob("*.yaml")) + list(scaffold_dir.rglob("*.yml"))
                if scaffold_dir.exists() else []
            )
            new_files = [f for f in yaml_files if f not in scaffold_yaml]

            logger.info(
                "codex done: rc=%d new_yaml=%d",
                result.returncode, len(new_files),
            )

            prompt_file.unlink(missing_ok=True)
            return True  # Always return True — scoring handles failures

        except subprocess.TimeoutExpired:
            logger.error("codex timed out after %ds", self.timeout)
            prompt_file.unlink(missing_ok=True)
            return False
        except FileNotFoundError:
            logger.error("codex binary not found at %s", self.codex_bin)
            prompt_file.unlink(missing_ok=True)
            return False
        except Exception:
            logger.exception("codex failed")
            prompt_file.unlink(missing_ok=True)
            return False


def _copy_scaffold(scaffold_dir: Path, output_dir: Path) -> None:
    """Copy scaffold files into output directory."""
    for item in scaffold_dir.iterdir():
        if item.name.startswith(".") and item.name != ".gitignore":
            continue
        if item.name == "__pycache__":
            continue
        dest = output_dir / item.name
        if item.is_dir():
            if not dest.exists():
                shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            if not dest.exists():
                shutil.copy2(item, dest)
