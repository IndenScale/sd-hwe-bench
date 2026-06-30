"""Workspace management for isolated rollout execution."""

from __future__ import annotations

import json
import shutil
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
    - manifest.json: run metadata
    """

    run_dir: Path
    task_id: str
    actor_name: str
    model: str | None = None

    @property
    def project_dir(self) -> Path:
        """Return the piki project directory inside the workspace."""
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
        (run_dir / "workspace").mkdir()

        ws = cls(run_dir=run_dir, task_id=task_id, actor_name=actor_name, model=model)

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
