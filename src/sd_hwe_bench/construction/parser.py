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


def _require_key(item: dict, file_name: str, object_path: str, key: str) -> object:
    if key not in item:
        raise ValueError(f"{file_name}: {object_path} missing required field '{key}'")
    return item[key]


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
            duration_days=int(
                _require_key(item, path.name, f"activities[{activity_id}]", "duration_days")
            ),
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
        resource_id = str(item.get("id", idx))
        resources.append(
            Resource(
                id=str(_require_key(item, path.name, f"resources[{resource_id}]", "id")),
                name=str(item.get("name", item.get("id", resource_id))),
                total_capacity=float(
                    _require_key(item, path.name, f"resources[{resource_id}]", "capacity")
                ),
                daily_cost_cny=float(
                    _require_key(
                        item, path.name, f"resources[{resource_id}]", "daily_cost_cny"
                    )
                ),
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
        activity_id = str(item.get("activity_id", idx))
        decisions.append(
            ContingencyDecision(
                activity_id=str(
                    _require_key(item, path.name, f"decisions[{activity_id}]", "activity_id")
                ),
                decision_type=str(
                    _require_key(item, path.name, f"decisions[{activity_id}]", "decision")
                ),
                params=_require_mapping(
                    item.get("params", {}),
                    path.name,
                    f"decisions[{activity_id}].params",
                ),
            )
        )
    return ContingencyPolicy(decisions=decisions)
