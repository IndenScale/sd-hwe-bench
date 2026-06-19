"""Deliverable critic: checks generator outputs."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.task import TaskInstance

# (config_key, filename_glob, default_category)
DELIVERABLE_PATHS: dict[str, tuple[str, str, str]] = {
    "bom-csv": ("bom-csv", "bom.csv", "采购清单"),
    "rack-face-panel-svg": ("rack-face-panel-svg", "rack-panel*.svg", "施工图"),
    "power-budget": ("power-budget", "power-budget.csv", "设计评审"),
    "cable-list": ("cable-list", "cable-list.csv", "采购清单"),
    "port-map": ("port-map", "port-map.csv", "设计评审"),
}


class DeliverableCritic(Critic):
    """Check whether piki generate produced expected deliverables."""

    name = "deliverable"

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        project_dir = workspace_root
        expected = task.metadata.expected_deliverables or []

        if not expected:
            return CriticResult(
                name=self.name,
                passed=True,
                score=1.0,
                comments=["No deliverables required for this task"],
            )

        dist_root = self._read_dist_root(project_dir)
        toml_targets = self._read_piki_toml_targets(project_dir)

        comments: list[str] = []
        found = 0

        for deliverable in expected:
            info = DELIVERABLE_PATHS.get(deliverable)
            if not info:
                comments.append(f"Unknown deliverable type: {deliverable}")
                continue

            config_key, filename_pattern, default_category = info
            category = toml_targets.get(config_key, default_category)
            category_dir = dist_root / category

            exists = False
            matched_file: str | None = None
            if category_dir.exists():
                for f in category_dir.rglob("*"):
                    if f.is_file() and fnmatch.fnmatch(f.name, filename_pattern):
                        exists = True
                        matched_file = f.name
                        break

            if exists:
                found += 1
                comments.append(f"✓ {deliverable}: {matched_file} found")
            else:
                comments.append(
                    f"✗ {deliverable}: {filename_pattern} missing (expected under {category_dir})"
                )

        total = len(expected)
        score = found / total if total > 0 else 1.0
        passed = found == total

        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
            artifacts={"found": found, "total": total},
        )

    def _read_dist_root(self, project_dir: Path) -> Path:
        piki_toml = project_dir / "piki.toml"
        if piki_toml.exists():
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
            try:
                data = tomllib.loads(piki_toml.read_text(encoding="utf-8"))
                return project_dir / data.get("generators", {}).get("dist", {}).get("root", "dist")
            except Exception:
                pass
        return project_dir / "dist"

    def _read_piki_toml_targets(self, project_dir: Path) -> dict[str, str]:
        piki_toml = project_dir / "piki.toml"
        if not piki_toml.exists():
            return {}
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        try:
            data = tomllib.loads(piki_toml.read_text(encoding="utf-8"))
            return data.get("generators", {}).get("dist", {}).get("targets", {})
        except Exception:
            return {}
