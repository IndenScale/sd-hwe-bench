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


def _relative_name(path: Path) -> str:
    return path.name


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing CPML file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{_relative_name(path)}: expected mapping at root")
    return data


def _require_list(value: object, file_name: str, field: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{file_name}: '{field}' must be a list")
    return value


def _require_mapping(value: object, file_name: str, field: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{file_name}: '{field}' must be a mapping")
    return value


def parse_schedule(path: Path) -> Schedule:
    """Parse schedule.yaml into a Schedule object."""
    data = _load_yaml(path)
    activities = []
    precedences = []
    for idx, item in enumerate(_require_list(data.get("activities", []), path.name, "activities")):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: activities[{idx}] must be a mapping")
        activity_id = str(item.get("id", idx))
        activity = Activity(
            id=activity_id,
            name=str(item.get("name", activity_id)),
            duration_days=int(item["duration_days"]),
            resource_requests=_require_mapping(
                item.get("resources", {}), path.name, f"activities[{activity_id}].resources"
            ),
            predecessors=_require_list(
                item.get("predecessors", []),
                path.name,
                f"activities[{activity_id}].predecessors",
            ),
            is_outdoor=bool(item.get("is_outdoor", False)),
            weather_delay_thresholds=_require_mapping(
                item.get("weather_limits", {}),
                path.name,
                f"activities[{activity_id}].weather_limits",
            ),
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
    for idx, item in enumerate(_require_list(data.get("resources", []), path.name, "resources")):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: resources[{idx}] must be a mapping")
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
    for idx, item in enumerate(_require_list(data.get("decisions", []), path.name, "decisions")):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: decisions[{idx}] must be a mapping")
        decisions.append(
            ContingencyDecision(
                activity_id=str(item["activity_id"]),
                decision_type=str(item["decision"]),
                params=_require_mapping(
                    item.get("params", {}),
                    path.name,
                    f"decisions[{item.get('activity_id', idx)}].params",
                ),
            )
        )
    return ContingencyPolicy(decisions=decisions)
