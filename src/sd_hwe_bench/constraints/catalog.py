"""Constraint catalog support for constraint-gap experiments.

The benchmark already has executable checks, but the paper experiments need the
checks to be countable objects: visible vs muted, executable vs offline, and
layer/family coverage.  This module provides a small adapter over task metadata
and optional ``constraints.yaml`` files without changing scoring semantics.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ConstraintSpec:
    """One applicable task constraint."""

    id: str
    family: str
    layer: str
    executable: bool = True
    critic: str = ""
    localization: str = "task-level"
    description: str = ""
    source: str = "inferred"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "layer": self.layer,
            "executable": self.executable,
            "critic": self.critic,
            "localization": self.localization,
            "description": self.description,
            "source": self.source,
        }


@dataclass(frozen=True)
class ConstraintSelector:
    """A selector used to mute constraints by id, family, or layer."""

    kind: str
    value: str

    def matches(self, spec: ConstraintSpec) -> bool:
        if self.kind == "id":
            return spec.id == self.value
        if self.kind == "family":
            return spec.family == self.value
        if self.kind == "layer":
            return spec.layer == self.value
        return False


class ConstraintCatalog:
    """List and query applicable constraints for one task."""

    def __init__(self, constraints: list[ConstraintSpec]):
        deduped: dict[str, ConstraintSpec] = {}
        for spec in constraints:
            deduped.setdefault(spec.id, spec)
        self.constraints = list(deduped.values())
        self.by_id = {spec.id: spec for spec in self.constraints}

    def selected(self, selectors: list[ConstraintSelector]) -> list[ConstraintSpec]:
        if not selectors:
            return []
        return [spec for spec in self.constraints if any(sel.matches(spec) for sel in selectors)]

    def visible_after(self, selectors: list[ConstraintSelector]) -> list[ConstraintSpec]:
        muted = {spec.id for spec in self.selected(selectors)}
        return [spec for spec in self.constraints if spec.id not in muted]

    def randomized(
        self,
        ratio: float,
        seed: int | None,
        only_executable: bool = True,
    ) -> list[ConstraintSpec]:
        """Return a deterministic random subset for mute experiments."""

        ratio = max(0.0, min(1.0, ratio))
        candidates = [
            spec for spec in self.constraints if spec.executable or not only_executable
        ]
        if ratio <= 0.0 or not candidates:
            return []
        rng = random.Random(seed)
        count = round(len(candidates) * ratio)
        count = min(len(candidates), max(1, count))
        return sorted(rng.sample(candidates, count), key=lambda s: s.id)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [spec.to_dict() for spec in self.constraints]

    def coverage_summary(self) -> dict[str, Any]:
        total = len(self.constraints)
        executable = sum(1 for spec in self.constraints if spec.executable)
        families = sorted({spec.family for spec in self.constraints})
        layers = sorted({spec.layer for spec in self.constraints})
        return {
            "total": total,
            "executable": executable,
            "non_executable": total - executable,
            "families": families,
            "layers": layers,
        }


def parse_constraint_selectors(raw: str | list[str] | None) -> list[ConstraintSelector]:
    """Parse comma-separated selectors.

    Accepted forms:
    - ``id:TELECOM-FK-001``
    - ``family:electrical``
    - ``layer:L3``
    - bare values, treated as ids
    """

    if raw is None:
        return []
    parts: list[str] = []
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
    else:
        for item in raw:
            parts.extend(p.strip() for p in str(item).split(","))

    selectors: list[ConstraintSelector] = []
    for part in parts:
        if not part:
            continue
        if ":" in part:
            kind, value = part.split(":", 1)
            kind = kind.strip()
            value = value.strip()
        else:
            kind, value = "id", part
        if kind not in {"id", "family", "layer"}:
            raise ValueError(f"unsupported constraint selector kind: {kind}")
        selectors.append(ConstraintSelector(kind=kind, value=value))
    return selectors


def build_constraint_catalog(task: Any) -> ConstraintCatalog:
    """Build a task constraint catalog from explicit or inferred sources."""

    explicit = _load_explicit_constraints(task)
    if explicit:
        return ConstraintCatalog(explicit)
    return ConstraintCatalog(_infer_constraints(task))


def _load_explicit_constraints(task: Any) -> list[ConstraintSpec]:
    meta = getattr(task, "metadata", None)
    specs: list[ConstraintSpec] = []

    raw_meta = getattr(meta, "constraints", None) if meta is not None else None
    if raw_meta:
        specs.extend(_coerce_specs(raw_meta, source="task.yaml"))

    task_dir = Path(getattr(task, "task_dir", ""))
    constraints_file = task_dir / "constraints.yaml"
    if constraints_file.exists():
        raw_file = yaml.safe_load(constraints_file.read_text(encoding="utf-8")) or {}
        entries = raw_file.get("constraints", raw_file) if isinstance(raw_file, dict) else raw_file
        specs.extend(_coerce_specs(entries, source="constraints.yaml"))

    return specs


def _coerce_specs(raw: Any, source: str) -> list[ConstraintSpec]:
    specs: list[ConstraintSpec] = []
    if not isinstance(raw, list):
        return specs
    for idx, item in enumerate(raw):
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or item.get("constraint_id") or f"{source}:{idx + 1}")
        specs.append(
            ConstraintSpec(
                id=cid,
                family=str(item.get("family") or item.get("constraint_family") or "unspecified"),
                layer=str(item.get("layer") or item.get("scoring_layer") or "unknown"),
                executable=bool(item.get("executable", True)),
                critic=str(item.get("critic") or item.get("rule") or ""),
                localization=str(item.get("localization") or item.get("localization_level") or "task-level"),
                description=str(item.get("description") or item.get("text") or ""),
                source=source,
            )
        )
    return specs


def _infer_constraints(task: Any) -> list[ConstraintSpec]:
    meta = getattr(task, "metadata", None)
    task_id = str(getattr(meta, "task_id", getattr(task, "task_id", "task")))
    scoring_layers = list(getattr(meta, "scoring_layers", []) or [])
    expected_deliverables = list(getattr(meta, "expected_deliverables", []) or [])
    evaluation = list(getattr(meta, "evaluation", []) or [])
    task_type = getattr(meta, "task_type", "")
    task_type = task_type.value if hasattr(task_type, "value") else str(task_type)
    expected_files = list(getattr(meta, "expected_files", []) or [])
    if not evaluation:
        evaluation = _default_analysis_specs(task_type, scoring_layers, expected_files)
    analysis_layers = {
        (spec.model_dump() if hasattr(spec, "model_dump") else dict(spec)).get("layer", "L4")
        for spec in evaluation
    }

    specs: list[ConstraintSpec] = []
    layer_family = {
        "L0": ("syntax", "syntax", "file-level"),
        "L1": ("schema", "piki", "field-level"),
        "L2": ("reference", "piki", "object-level"),
        "L3": ("static", "piki", "object-level"),
        "L4": ("dynamic", "analysis", "task-level"),
        "L5": ("layout", "piki", "object-level"),
        "L6": ("reserved", "", "task-level"),
    }

    for layer in scoring_layers or ["L0", "L1", "L2", "L3", "L4", "L5"]:
        if layer == "Deliverable" or layer.startswith("L7"):
            continue
        if layer in analysis_layers:
            continue
        family, critic, localization = layer_family.get(layer, ("unspecified", "", "task-level"))
        specs.append(
            ConstraintSpec(
                id=f"{task_id}:{layer}",
                family=family,
                layer=layer,
                executable=bool(critic),
                critic=critic,
                localization=localization,
                description=f"Inferred scoring-layer constraint for {layer}",
            )
        )

    for idx, spec in enumerate(evaluation, start=1):
        d = spec.model_dump() if hasattr(spec, "model_dump") else dict(spec)
        layer = str(d.get("layer", "L4"))
        critic = str(d.get("critic", "analysis"))
        specs.append(
            ConstraintSpec(
                id=f"{task_id}:{critic}:{idx}",
                family=_family_for_critic(critic),
                layer=layer,
                executable=True,
                critic=critic,
                localization="task-level",
                description=f"Inferred analysis critic constraint for {critic}",
            )
        )

    for deliverable in expected_deliverables:
        specs.append(
            ConstraintSpec(
                id=f"{task_id}:deliverable:{deliverable}",
                family="deliverable",
                layer="Deliverable",
                executable=True,
                critic="deliverable",
                localization="file-level",
                description=f"Required deliverable {deliverable}",
            )
        )

    return specs


def _default_analysis_specs(
    task_type: str,
    scoring_layers: list[str],
    expected_files: list[str],
) -> list[dict[str, str]]:
    has_l4 = "L4" in scoring_layers or "L7-Performance" in scoring_layers
    specs: list[dict[str, str]] = []
    if task_type == "conceptual-design" and has_l4:
        specs.append({"critic": "decision", "layer": "L4"})
    elif task_type == "epc" and has_l4:
        specs.append({"critic": "epc", "layer": "L4"})
    elif has_l4:
        specs.append({"critic": "aidc-performance", "layer": "L4"})

    if task_type == "detailed-design" or any("construction/" in f for f in expected_files):
        specs.append({"critic": "constructability", "layer": "L5"})
    return specs


def _family_for_critic(critic: str) -> str:
    return {
        "aidc-performance": "thermal",
        "epc": "schedule",
        "constructability": "construction",
        "decision": "decision",
    }.get(critic, "analysis")
