"""Gemini CLI agent driver for SD-HWE-Bench.

Invokes `gemini` in non-interactive mode (-p/--prompt) with a task prompt.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GeminiDriver:
    """Run a single benchmark task via Gemini CLI."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        timeout_seconds: int = 600,
        gemini_bin: str = "gemini",
    ):
        self.model = model
        self.timeout = timeout_seconds
        self.gemini_bin = gemini_bin

    def run(
        self,
        prompt: str,
        scaffold_dir: Path,
        output_dir: Path,
    ) -> bool:
        """Run the agent on a task.

        Copies scaffold into output_dir, invokes gemini --prompt,
        and leaves the agent's output files in output_dir.

        Returns True if the agent completed without timeout/error.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy scaffold
        if scaffold_dir.exists():
            _copy_scaffold(scaffold_dir, output_dir)

        # Init git repo (gemini CLI requires a git repo for tool access)
        git_dir = output_dir / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init", "-q"],
                    cwd=output_dir,
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=output_dir,
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["git", "commit", "-m", "scaffold", "--allow-empty", "-q"],
                    cwd=output_dir,
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                logger.warning("Failed to init git repo for gemini", exc_info=True)

        # Build command
        cmd = [
            self.gemini_bin,
            "--prompt", prompt,
            "--model", self.model,
            "--yolo",
            "--skip-trust",
            "--output-format", "text",
        ]

        env = os.environ.copy()

        try:
            logger.info(
                "Running gemini: model=%s cwd=%s timeout=%ds",
                self.model, output_dir, self.timeout,
            )

            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=output_dir,
                env=env,
            )

            # Log diagnostics
            stderr_lines = result.stderr.strip().split("\n")
            for line in stderr_lines[-5:]:
                if line.strip():
                    logger.debug("gemini stderr: %s", line[:200])

            yaml_files = list(output_dir.rglob("*.yaml")) + list(output_dir.rglob("*.yml"))
            scaffold_yaml = (
                list(scaffold_dir.rglob("*.yaml")) + list(scaffold_dir.rglob("*.yml"))
                if scaffold_dir.exists()
                else []
            )
            new_files = [f for f in yaml_files if f not in scaffold_yaml]

            logger.info(
                "gemini completed: returncode=%d, new_yaml_files=%d",
                result.returncode, len(new_files),
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("gemini timed out after %ds", self.timeout)
            return False
        except FileNotFoundError:
            logger.error("gemini binary not found at %s", self.gemini_bin)
            return False
        except Exception:
            logger.exception("gemini failed")
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
