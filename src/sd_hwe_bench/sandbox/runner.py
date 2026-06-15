"""Sandbox runner for executing piki commands locally or in containers."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

SandboxBackend = Literal["none", "docker", "podman"]


@dataclass
class PikiResult:
    """Result of a piki command execution."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    parsed: dict | None = None
    available: bool = True

    @property
    def success(self) -> bool:
        return self.returncode == 0


class SandboxRunner:
    """Run piki commands in an isolated environment.

    - backend='none': run piki directly on the host (uses PIPKIPATH env var or PATH).
    - backend='docker'/'podman': run piki inside a container image with the workspace mounted.
    """

    def __init__(
        self,
        backend: SandboxBackend = "none",
        image: str = "sd-hwe-bench-piki:latest",
        piki_python: str | None = None,
    ):
        self.backend = backend
        self.image = image
        self.piki_python = piki_python or os.environ.get(
            "PIPKIPATH", "/Users/indenscale/workspace/piki/.venv/bin/python"
        )

    def check(self, project_dir: Path) -> PikiResult:
        """Run `piki check --format json` on project_dir."""
        return self._run_piki(project_dir, "check", ["--format", "json"])

    def generate(self, project_dir: Path) -> PikiResult:
        """Run `piki generate` on project_dir."""
        return self._run_piki(project_dir, "generate", [])

    def _run_piki(
        self,
        project_dir: Path,
        subcommand: str,
        extra_args: list[str],
    ) -> PikiResult:
        project_dir = Path(project_dir).resolve()

        if self.backend in ("docker", "podman"):
            return self._run_in_container(project_dir, subcommand, extra_args)

        return self._run_on_host(project_dir, subcommand, extra_args)

    def _run_on_host(
        self,
        project_dir: Path,
        subcommand: str,
        extra_args: list[str],
    ) -> PikiResult:
        # Prefer explicit Python module path (local editable install)
        python = self.piki_python
        if python and Path(python).exists():
            cmd = [python, "-m", "piki", subcommand, *extra_args]
        elif shutil.which("piki"):
            cmd = ["piki", subcommand, *extra_args]
        else:
            logger.error("piki not found: PIPKIPATH=%s and 'piki' not in PATH", python)
            return PikiResult(
                command=[],
                returncode=-1,
                stdout="",
                stderr="piki not found",
                available=False,
            )

        logger.debug("Running piki on host: %s in %s", " ".join(cmd), project_dir)
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        parsed = None
        if "--format json" in " ".join(extra_args) or subcommand == "check":
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = None

        return PikiResult(
            command=cmd,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            parsed=parsed,
            available=True,
        )

    def _run_in_container(
        self,
        project_dir: Path,
        subcommand: str,
        extra_args: list[str],
    ) -> PikiResult:
        runtime = "docker" if self.backend == "docker" else "podman"

        if shutil.which(runtime) is None:
            logger.warning("%s not found, falling back to host piki", runtime)
            return self._run_on_host(project_dir, subcommand, extra_args)

        # Mount workspace into /work inside container
        cmd = [
            runtime,
            "run",
            "--rm",
            "-v",
            f"{project_dir}:/work",
            "-w",
            "/work",
            self.image,
            "python",
            "-m",
            "piki",
            subcommand,
            *extra_args,
        ]

        logger.debug("Running piki in %s: %s", runtime, " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
        )
        parsed = None
        if "--format json" in " ".join(extra_args) or subcommand == "check":
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = None

        return PikiResult(
            command=cmd,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            parsed=parsed,
            available=True,
        )
