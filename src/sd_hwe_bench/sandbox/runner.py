"""Sandbox runner for executing piki commands locally or in containers."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sd_hwe_bench.settings import settings

logger = logging.getLogger(__name__)

SandboxBackend = Literal["auto", "none", "docker", "podman"]


def detect_backend() -> SandboxBackend:
    """Detect the best available sandbox backend.

    Order follows AGENTS.md: docker → podman → none.
    """
    if shutil.which("docker"):
        return "docker"
    if shutil.which("podman"):
        return "podman"
    return "none"


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


def _current_python_has_piki() -> bool:
    """Check whether the current interpreter can import piki."""
    try:
        import piki  # noqa: F401

        return True
    except ImportError:
        return False


class SandboxRunner:
    """Run piki commands in an isolated environment.

    - backend='auto': detect docker → podman → none at runtime.
    - backend='none': run piki directly on the host.
      Resolution order: explicit ``piki_python`` > current interpreter (if piki
      is importable) > ``$PIPKIPATH`` > ``piki`` executable on PATH.
    - backend='docker'/'podman': run piki inside a container image with the workspace mounted.

    Environment variables can be injected into the sandbox via ``env_vars``.
    These are passed to the host subprocess for ``backend='none'`` and as
    ``-e KEY=VALUE`` flags for ``backend='docker'/'podman'``.
    """

    def __init__(
        self,
        backend: SandboxBackend | None = None,
        image: str | None = None,
        piki_python: str | None = None,
        env_vars: dict[str, str] | None = None,
    ):
        self.backend = detect_backend() if backend is None or backend == "auto" else backend
        self.image = image if image is not None else settings.DEFAULT_SANDBOX_IMAGE
        self.piki_python = piki_python
        self.env_vars = dict(env_vars) if env_vars else {}

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

    def _resolve_python(self) -> str | None:
        """Return the Python interpreter to use for running piki.

        Resolution order:
        1. Explicit ``piki_python`` passed to the runner.
        2. Current interpreter if it can import piki.
        3. ``SD_HWE_PIKI_PYTHON`` environment variable.
        4. Legacy ``PIPKIPATH`` environment variable.
        5. ``python3`` / ``python`` on PATH.
        """
        # 1. Explicit override wins.
        if self.piki_python:
            return self.piki_python

        # 2. Prefer current interpreter if piki/adl are installed in it.
        if _current_python_has_piki():
            return sys.executable

        # 3. Environment-based resolution.
        env_python = settings.PIKI_PYTHON
        if env_python and Path(env_python).exists():
            return env_python

        # 4. Fall back to PATH.
        path_python = shutil.which("python3") or shutil.which("python")
        if path_python:
            return path_python

        return None

    def _run_on_host(
        self,
        project_dir: Path,
        subcommand: str,
        extra_args: list[str],
    ) -> PikiResult:
        python = self._resolve_python()
        if python:
            cmd = [python, "-m", "piki", subcommand, *extra_args]
        elif shutil.which("piki"):
            cmd = ["piki", subcommand, *extra_args]
        else:
            logger.error(
                "piki not found: not importable in current interpreter, "
                "SD_HWE_PIKI_PYTHON/PIPKIPATH not set, and 'piki' not in PATH"
            )
            return PikiResult(
                command=[],
                returncode=-1,
                stdout="",
                stderr="piki not found",
                available=False,
            )

        env = os.environ.copy()
        env.update(self.env_vars)
        logger.debug(
            "Running piki on host: %s in %s (with %d injected env vars)",
            " ".join(cmd),
            project_dir,
            len(self.env_vars),
        )
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=settings.PIKI_TIMEOUT_S,
            env=env,
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

        # Mount workspace into the configured container workdir and inject env vars.
        workdir = settings.CONTAINER_WORKDIR
        cmd = [
            runtime,
            "run",
            "--rm",
            "-v",
            f"{project_dir}:{workdir}",
            "-w",
            workdir,
        ]
        for key, value in self.env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend(
            [
                self.image,
                "python",
                "-m",
                "piki",
                subcommand,
                *extra_args,
            ]
        )

        logger.debug(
            "Running piki in %s: %s (with %d injected env vars)",
            runtime,
            " ".join(cmd),
            len(self.env_vars),
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.CONTAINER_TIMEOUT_S,
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
