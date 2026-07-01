"""Workspace management for isolated rollout execution."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Workspace:
    """An isolated workspace for a single Actor rollout.

    A workspace is a directory on disk that contains:
    - workspace/: the actual piki project directory (scaffold + actor outputs)
    - prompt.md: the injected prompt
    - trajectory.jsonl: actor interaction log
    - actor_output.log: full (untruncated) actor stdout/stderr per phase
    - manifest.json: run metadata

    When ``work_dir`` is set (actor isolation), the live ``workspace/`` lives
    under ``work_dir`` — a directory *outside* the benchmark repo containing only
    the scaffold — while run metadata stays under ``run_dir``.  Call
    :meth:`archive_project_dir` after scoring to copy the produced files back
    into ``run_dir/workspace`` for archival.
    """

    run_dir: Path
    task_id: str
    actor_name: str
    model: str | None = None
    work_dir: Path | None = None

    @property
    def project_dir(self) -> Path:
        """Return the piki project directory the actor runs in."""
        if self.work_dir is not None:
            return self.work_dir / "workspace"
        return self.run_dir / "workspace"

    @property
    def prompt_path(self) -> Path:
        return self.run_dir / "prompt.md"

    @property
    def trajectory_path(self) -> Path:
        return self.run_dir / "trajectory.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    @property
    def actor_output_path(self) -> Path:
        return self.run_dir / "actor_output.log"

    @classmethod
    def create(
        cls,
        run_root: Path,
        task_id: str,
        actor_name: str,
        model: str | None = None,
        scaffold_dir: Path | None = None,
        attempt: int | None = None,
        scaffold_excludes: list[str] | None = None,
        isolate: bool = False,
        work_root: Path | None = None,
    ) -> Workspace:
        """Create a new workspace directory.

        Args:
            run_root: Parent directory for all run archives (e.g., ./runs).
            task_id: Task identifier, used in the directory name.
            actor_name: Name of the actor (e.g., 'kimi').
            model: Optional model name.
            scaffold_dir: Optional scaffold directory to copy into workspace.
            attempt: Optional attempt index to make the directory name unique
                when multiple rollouts run in parallel.
            scaffold_excludes: Optional top-level scaffold entries to omit.
            isolate: When True, place the live ``workspace/`` under ``work_root``
                (outside the benchmark repo) so the actor has no path to the
                reference solutions; run metadata stays under ``run_root``.
            work_root: Parent dir for isolated working copies. Defaults to the
                system temp dir when isolation is requested without an explicit
                root.
        """
        run_root = Path(run_root)
        run_root.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_task = task_id.replace("/", "_")
        safe_actor = actor_name.replace("/", "_")
        safe_model = model.replace("/", "_").replace(":", "_") if model else ""
        suffix = f"_{safe_model}" if safe_model else ""
        attempt_suffix = f"_a{attempt:03d}" if attempt is not None else ""
        run_name = f"{timestamp}_{safe_task}_{safe_actor}{suffix}{attempt_suffix}"
        run_dir = run_root / run_name

        if run_dir.exists():
            raise FileExistsError(f"Workspace already exists: {run_dir}")

        run_dir.mkdir(parents=True)

        work_dir: Path | None = None
        if isolate:
            wr = Path(work_root) if work_root else Path(tempfile.gettempdir()) / "sd-hwe-bench-work"
            wr.mkdir(parents=True, exist_ok=True)
            work_dir = wr / run_name
            # Guard against a name collision in the shared work root.
            if work_dir.exists():
                work_dir = wr / f"{run_name}_p{os.getpid()}"
            (work_dir / "workspace").mkdir(parents=True)
        else:
            (run_dir / "workspace").mkdir()

        ws = cls(
            run_dir=run_dir,
            task_id=task_id,
            actor_name=actor_name,
            model=model,
            work_dir=work_dir,
        )

        if scaffold_dir is not None and scaffold_dir.exists():
            ws.copy_scaffold(scaffold_dir, excludes=scaffold_excludes)

        ws.write_manifest(
            {
                "version": "2",
                "task_id": task_id,
                "actor": actor_name,
                "model": model,
                "attempt": attempt,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "isolated": isolate,
                "work_dir": str(work_dir) if work_dir else None,
            }
        )

        return ws

    def copy_scaffold(self, scaffold_dir: Path, excludes: list[str] | None = None) -> None:
        """Copy scaffold files into the workspace project directory."""
        scaffold_dir = Path(scaffold_dir)
        if not scaffold_dir.exists():
            return
        excluded = set(excludes or [])
        for item in scaffold_dir.iterdir():
            if item.name in excluded:
                continue
            if item.name.startswith(".") and item.name != ".gitignore":
                continue
            if item.name == "__pycache__":
                continue
            dest = self.project_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    def write_prompt(self, prompt: str) -> None:
        """Persist the injected prompt."""
        self.prompt_path.write_text(prompt, encoding="utf-8")

    def append_actor_log(self, phase: str, text: str) -> None:
        """Append the full (untruncated) actor transcript for a phase.

        The trajectory log only keeps a short preview; this captures everything
        so a timed-out or failed run remains diagnosable.
        """
        header = f"\n===== {phase} @ {datetime.now(timezone.utc).isoformat()} =====\n"
        with self.actor_output_path.open("a", encoding="utf-8") as f:
            f.write(header)
            f.write(text or "")
            f.write("\n")

    def archive_project_dir(self, cleanup: bool = False) -> None:
        """Copy an isolated (out-of-repo) project dir back into ``run_dir/workspace``.

        No-op when the workspace is not isolated.  Keeps run archives
        self-contained for ``ArchiveManager`` / ``tools/audit_runs.py``.  When
        ``cleanup`` is True, the out-of-repo working copy is removed afterward.
        """
        if self.work_dir is None:
            return
        dest = self.run_dir / "workspace"
        if dest.exists():
            shutil.rmtree(dest)
        if self.project_dir.exists():
            shutil.copytree(self.project_dir, dest)
        else:
            dest.mkdir(parents=True, exist_ok=True)
        if cleanup:
            shutil.rmtree(self.work_dir, ignore_errors=True)

    def log_trajectory(self, entry: dict[str, Any]) -> None:
        """Append a JSON line to the trajectory log."""
        entry["_ts"] = datetime.now(timezone.utc).isoformat()
        with self.trajectory_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def write_manifest(self, data: dict[str, Any]) -> None:
        """Write/overwrite the manifest file."""
        self.manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def read_manifest(self) -> dict[str, Any]:
        """Read the manifest file."""
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def update_manifest(self, data: dict[str, Any]) -> None:
        """Merge new data into the manifest and write it back."""
        manifest = self.read_manifest()
        manifest.update(data)
        self.write_manifest(manifest)

    def list_files(self) -> list[Path]:
        """List all files in the project directory."""
        if not self.project_dir.exists():
            return []
        return sorted(p for p in self.project_dir.rglob("*") if p.is_file())
