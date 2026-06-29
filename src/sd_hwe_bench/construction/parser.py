"""Parse CPML YAML files produced by agents."""

from __future__ import annotations

from pathlib import Path

import yaml

from sd_hwe_bench.construction.cpml import (
    Activity,
    ContingencyDecision,
    ContingencyPolicy,
    Precedence,
    Resource,
    ResourcePlan,
    Schedule,
)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing CPML file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_schedule(path: Path) -> Schedule:
    """Parse schedule.yaml into a Schedule object."""
    data = _load_yaml(path)
    activities = []
    precedences = []
    for item in data.get("activities", []):
        activity = Activity(
            id=str(item["id"]),
            name=str(item.get("name", item["id"])),
            duration_days=int(item["duration_days"]),
            resource_requests=dict(item.get("resources", {})),
            predecessors=list(item.get("predecessors", [])),
            is_outdoor=bool(item.get("is_outdoor", False)),
            weather_delay_thresholds=dict(item.get("weather_limits", {})),
        )
        activities.append(activity)
        for pred in activity.predecessors:
            precedences.append(
                Precedence(
                    from_id=str(pred),
                    to_id=activity.id,
                    lag_days=int(item.get("lag_days", 0)),
                )
            )
    return Schedule(activities=activities, precedences=precedences)


def parse_resource_plan(path: Path) -> ResourcePlan:
    """Parse resource-plan.yaml into a ResourcePlan object."""
    data = _load_yaml(path)
    resources = []
    for item in data.get("resources", []):
        resources.append(
            Resource(
                id=str(item["id"]),
                name=str(item.get("name", item["id"])),
                total_capacity=float(item["capacity"]),
                daily_cost_cny=float(item["daily_cost_cny"]),
            )
        )
    return ResourcePlan(resources=resources)


def parse_contingency_policy(path: Path) -> ContingencyPolicy:
    """Parse contingency-policy.yaml into a ContingencyPolicy object."""
    data = _load_yaml(path)
    decisions = []
    for item in data.get("decisions", []):
        decisions.append(
            ContingencyDecision(
                activity_id=str(item["activity_id"]),
                decision_type=str(item["decision"]),
                params=dict(item.get("params", {})),
            )
        )
    return ContingencyPolicy(decisions=decisions)
