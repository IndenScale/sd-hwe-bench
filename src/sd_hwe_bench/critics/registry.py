"""Declarative critic registry.

Resolves which *analysis* critics (the L4/L5 dynamic-model, performance, EPC
schedule, constructability, and conceptual-design decision checks) run for a
given task, and builds them.

This replaces the hardcoded ``if task_type == "epc"`` / ``elif "L4" in ...`` /
``if task_type == "detailed-design"`` dispatch that used to live inline in
``scorer.py``.  Adding a new analysis critic now means:

1. write a ``Critic`` subclass,
2. register a builder in ``CRITIC_BUILDERS``,
3. either add a default rule in ``resolve_analysis_critics`` or have tasks
   declare it explicitly via ``task.yaml``'s ``evaluation:`` block.

The generic layers (L0 syntax, L1-L5 piki, L3 numeric, deliverable, rubric)
remain wired directly in ``scorer.py`` because they are task-agnostic.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Callable

from sd_hwe_bench.critics.base import Critic
from sd_hwe_bench.critics.constructability import ConstructabilityCritic
from sd_hwe_bench.critics.decision import DecisionCritic
from sd_hwe_bench.critics.epc import EPCCritic


@dataclasses.dataclass
class AnalysisSpec:
    """A declarative spec for one analysis critic bound to a scoring layer."""

    critic: str
    layer: str = "L4"
    mode: str = "replace"  # "replace" overwrites the layer; "merge" combines with existing
    provides_performance: bool = False
    params: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CriticContext:
    """Context handed to critic builders."""

    project_dir: Path
    l7_config: dict
    repo_root: Path


# ── Builders ──────────────────────────────────────────────────────────────


def _build_epc(spec: AnalysisSpec, ctx: CriticContext) -> Critic:
    deadline = spec.params.get("deadline_days", ctx.l7_config.get("deadline_days", 180))
    return EPCCritic(deadline_days=deadline)


def _build_constructability(spec: AnalysisSpec, ctx: CriticContext) -> Critic:
    return ConstructabilityCritic()


def _build_decision(spec: AnalysisSpec, ctx: CriticContext) -> Critic:
    """Build the conceptual-design multi-scheme DecisionCritic.

    The scheme library (answer key) and scenario weights live on the task
    metadata and are read by the critic at evaluate() time, so the builder only
    forwards an optional tolerance override from the spec params.
    """
    return DecisionCritic(tolerance=spec.params.get("tolerance"))


def _build_aidc_performance(spec: AnalysisSpec, ctx: CriticContext) -> Critic:
    """Build the AIDC thermal/LCC performance critic.

    Encapsulates the weather / canonical-project / objective-weight resolution
    that used to be inline in scorer.py (including the hardcoded ``datacenter-hall``
    default and the ``rooms/`` co-design detection).
    """
    from sd_hwe_bench.critics.performance import PerformanceCritic
    from sd_hwe_bench.simulation.model import AIDCWeatherProfile

    cfg = ctx.l7_config
    weather_type = cfg.get("weather", "summer")
    sim_hours = cfg.get("hours", 48)
    weights = cfg.get("objective_weights", [0.3, 0.3, 0.15, 0.25])

    if weather_type == "winter":
        weather = AIDCWeatherProfile.synthetic_winter_day()
    else:
        weather = AIDCWeatherProfile.synthetic_summer_day()

    canonical_cfg = cfg.get("canonical_project", "datacenter-hall")
    canonical_dir = ctx.repo_root / "canonical" / canonical_cfg
    # Co-design tasks ship their own room model in the workspace; otherwise the
    # canonical project supplies the room.
    if (ctx.project_dir / "rooms").exists() and any((ctx.project_dir / "rooms").glob("*.yaml")):
        perf_project_dir = None
    else:
        perf_project_dir = canonical_dir

    return PerformanceCritic(
        project_dir=perf_project_dir,
        canonical_project=canonical_dir,
        weather=weather,
        simulation_hours=sim_hours,
        objective_weights=weights,
        reference=cfg.get("reference"),
    )


CRITIC_BUILDERS: dict[str, Callable[[AnalysisSpec, CriticContext], Critic]] = {
    "epc": _build_epc,
    "aidc-performance": _build_aidc_performance,
    "constructability": _build_constructability,
    "decision": _build_decision,
}


def build_critic(spec: AnalysisSpec, ctx: CriticContext) -> Critic:
    try:
        builder = CRITIC_BUILDERS[spec.critic]
    except KeyError as exc:
        raise ValueError(
            f"Unknown analysis critic '{spec.critic}'. Registered: {sorted(CRITIC_BUILDERS)}"
        ) from exc
    return builder(spec, ctx)


def build_context(task: Any, project_dir: Path) -> CriticContext:
    import sd_hwe_bench

    repo_root = Path(sd_hwe_bench.__file__).parent.parent.parent
    l7: dict = {}
    if hasattr(task, "metadata"):
        l7 = getattr(task.metadata, "l7_config", {}) or getattr(task.metadata, "l4_config", {}) or {}
    return CriticContext(project_dir=Path(project_dir), l7_config=l7, repo_root=repo_root)


# ── Resolution ──────────────────────────────────────────────────────────────


def _task_type_value(meta: Any) -> str:
    tt = getattr(meta, "task_type", None) if meta is not None else None
    if tt is None:
        return ""
    return tt.value if hasattr(tt, "value") else str(tt)


def resolve_analysis_critics(task: Any) -> list[AnalysisSpec]:
    """Resolve the ordered list of analysis-critic specs for a task.

    Priority:
      1. Explicit ``task.metadata.evaluation`` (overrides defaults).
      2. Defaults derived from ``task_type`` + ``scoring_layers`` + ``expected_files``
         — reproduces the legacy if/elif dispatch exactly.

    L4 specs are emitted before L5 specs so the run order matches the old code.
    """
    meta = getattr(task, "metadata", None)

    # 1. Explicit override.
    explicit = getattr(meta, "evaluation", None) if meta is not None else None
    if explicit:
        specs: list[AnalysisSpec] = []
        for e in explicit:
            d = e.model_dump() if hasattr(e, "model_dump") else dict(e)
            specs.append(
                AnalysisSpec(
                    critic=d["critic"],
                    layer=d.get("layer", "L4"),
                    mode=d.get("mode", "replace"),
                    provides_performance=d.get("provides_performance", False),
                    params=d.get("params", {}) or {},
                )
            )
        return specs

    # 2. Derive from task_type (legacy behavior).
    task_type = _task_type_value(meta)
    scoring_layers = list(getattr(meta, "scoring_layers", []) or []) if meta is not None else []
    expected_files = list(getattr(meta, "expected_files", []) or []) if meta is not None else []
    has_l4 = "L4" in scoring_layers or "L7-Performance" in scoring_layers

    specs = []
    if task_type == "conceptual-design" and has_l4:
        specs.append(
            AnalysisSpec(critic="decision", layer="L4", mode="replace", provides_performance=True)
        )
    elif task_type == "epc" and has_l4:
        specs.append(
            AnalysisSpec(critic="epc", layer="L4", mode="replace", provides_performance=True)
        )
    elif has_l4:
        specs.append(
            AnalysisSpec(
                critic="aidc-performance", layer="L4", mode="replace", provides_performance=True
            )
        )

    if task_type == "detailed-design" or any("construction/" in f for f in expected_files):
        specs.append(
            AnalysisSpec(
                critic="constructability", layer="L5", mode="merge", provides_performance=False
            )
        )

    return specs
