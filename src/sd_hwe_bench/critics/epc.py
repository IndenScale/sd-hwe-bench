"""EPC (Engineering, Procurement, Construction) critic for AIDC tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sd_hwe_bench.construction.events import (
    generate_scenarios,
    generate_supply_delays,
    generate_weather_profile,
)
from sd_hwe_bench.construction.evaluator import evaluate_schedule
from sd_hwe_bench.construction.parser import (
    parse_contingency_policy,
    parse_resource_plan,
    parse_schedule,
)
from sd_hwe_bench.construction.scheduler import run_schedule
from sd_hwe_bench.critics.base import Critic, CriticResult


class EPCCritic(Critic):
    """Evaluate construction master schedule, resource plan, and contingency policy."""

    name = "EPC"

    def __init__(self, deadline_days: int = 180, n_scenarios: int = 20):
        self.deadline_days = deadline_days
        self.n_scenarios = n_scenarios

    def evaluate(self, workspace_root: Path, task: Any) -> CriticResult:
        """Parse CPML files, run deterministic baseline and stochastic scenarios."""
        schedule_path = workspace_root / "schedule.yaml"
        resource_path = workspace_root / "resource-plan.yaml"
        contingency_path = workspace_root / "contingency-policy.yaml"

        comments: list[str] = []

        schema_violations = self._schema_contract_violations(
            schedule_path=schedule_path,
            resource_path=resource_path,
            contingency_path=contingency_path,
        )

        # 1. Parse files.
        try:
            schedule = parse_schedule(schedule_path)
            resource_plan = parse_resource_plan(resource_path)
            contingency_policy = parse_contingency_policy(contingency_path)
        except FileNotFoundError as exc:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=[f"Missing required CPML file: {exc.filename}"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=[*schema_violations, f"CPML parse error: {exc}"],
            )

        # Read task config if available.
        task_config = getattr(task.metadata, "l7_config", {}) if hasattr(task, "metadata") else {}
        if isinstance(task_config, dict):
            self.deadline_days = task_config.get("deadline_days", self.deadline_days)

        activity_ids = {a.id for a in schedule.activities}

        # 2. Deterministic baseline simulation.
        baseline_weather = generate_weather_profile(self.deadline_days)
        baseline = run_schedule(
            schedule=schedule,
            resource_plan=resource_plan,
            weather=baseline_weather,
            supply_delays=[],
            contingency_policy=contingency_policy,
            horizon_days=self.deadline_days,
        )

        baseline_eval = evaluate_schedule(
            baseline, resource_plan, schedule, deadline_days=self.deadline_days
        )

        # 3. Hard constraints.
        hard_violations: list[str] = []
        if baseline.makespan_days > self.deadline_days:
            hard_violations.append(
                f"Deterministic makespan {baseline.makespan_days}d "
                f"exceeds deadline {self.deadline_days}d"
            )
        if not baseline.all_scheduled:
            hard_violations.append("Not all activities scheduled in deterministic run")
        for violation in baseline.violations:
            if "over capacity" in violation:
                hard_violations.append(violation)

        # Contingency policy must be non-empty and reference valid activities.
        hard_violations.extend(schema_violations)
        if not contingency_policy.decisions:
            hard_violations.append("Contingency policy is empty")
        else:
            for decision in contingency_policy.decisions:
                if decision.activity_id not in activity_ids:
                    hard_violations.append(
                        f"Contingency decision references unknown activity {decision.activity_id}"
                    )
                if decision.decision_type not in {
                    "wait",
                    "defer-shipment",
                    "skip-to-later",
                }:
                    hard_violations.append(
                        f"Unknown contingency decision type {decision.decision_type} "
                        f"for {decision.activity_id}"
                    )

        passed = len(hard_violations) == 0

        # 4. Stochastic scenarios (weather + supply-chain delays).
        sla_met_count = 0
        scenarios = generate_scenarios(n=self.n_scenarios, horizon_days=self.deadline_days)
        for idx, scenario in enumerate(scenarios):
            scenario.supply_delays = generate_supply_delays(
                schedule.activities, seed=idx
            )
            result = run_schedule(
                schedule=schedule,
                resource_plan=resource_plan,
                weather=scenario.weather,
                supply_delays=scenario.supply_delays,
                contingency_policy=contingency_policy,
                horizon_days=self.deadline_days,
            )
            evaluation = evaluate_schedule(
                result, resource_plan, schedule, deadline_days=self.deadline_days
            )
            if evaluation["sla_met"]:
                sla_met_count += 1

        score = sla_met_count / self.n_scenarios if self.n_scenarios > 0 else 0.0

        comments = [
            f"Deterministic makespan: {baseline.makespan_days}d",
            f"Deterministic total cost: {baseline_eval['total_cost_cny']:,.0f} CNY",
            f"SLA met in {sla_met_count}/{self.n_scenarios} stochastic scenarios",
            f"Score (avg SLA met): {score:.2%}",
        ]
        if hard_violations:
            comments = hard_violations + comments

        artifacts = {
            "baseline": baseline_eval,
            "deterministic_violations": baseline.violations,
        }

        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
            artifacts=artifacts,
        )

    def _schema_contract_violations(
        self,
        schedule_path: Path,
        resource_path: Path,
        contingency_path: Path,
    ) -> list[str]:
        """Return field-level CPML schema diagnostics for common alias drift."""

        violations: list[str] = []
        schedule_data = self._safe_load_mapping(schedule_path, violations)
        if schedule_data is not None:
            activities = schedule_data.get("activities", [])
            if isinstance(activities, list):
                prerequisites_ids: list[str] = []
                resource_requirement_ids: list[str] = []
                weather_alias_ids: list[str] = []
                for idx, item in enumerate(activities):
                    if not isinstance(item, dict):
                        continue
                    activity_id = str(item.get("id", idx))
                    for field in ("id", "duration_days"):
                        if field not in item:
                            violations.append(
                                f"schedule.yaml activities[{activity_id}]: missing required field "
                                f"'{field}'"
                            )
                    if "predecessors" not in item and "prerequisites" in item:
                        prerequisites_ids.append(activity_id)
                    if "resources" not in item and "resource_requirements" in item:
                        resource_requirement_ids.append(activity_id)
                    if "weather_limits" not in item and (
                        "max_wind_speed_m_s" in item
                        or "max_precipitation_mm_per_h" in item
                        or "weather_sensitive" in item
                    ):
                        weather_alias_ids.append(activity_id)
                    if "resources" not in item:
                        violations.append(
                            f"schedule.yaml activities[{activity_id}]: missing required field "
                            "'resources' mapping"
                        )
                    elif not isinstance(item.get("resources"), dict):
                        violations.append(
                            f"schedule.yaml activities[{activity_id}].resources: expected mapping"
                        )
                    if "weather_limits" in item and not isinstance(item.get("weather_limits"), dict):
                        violations.append(
                            f"schedule.yaml activities[{activity_id}].weather_limits: expected mapping"
                        )
                if prerequisites_ids:
                    violations.append(
                        "schedule.yaml: expected field 'predecessors'; found "
                        f"'prerequisites' in activities {_format_ids(prerequisites_ids)} "
                        "(ignored by CPML parser)"
                    )
                if resource_requirement_ids:
                    violations.append(
                        "schedule.yaml: expected field 'resources'; found "
                        f"'resource_requirements' in activities {_format_ids(resource_requirement_ids)} "
                        "(ignored by CPML parser)"
                    )
                if weather_alias_ids:
                    violations.append(
                        "schedule.yaml: expected field 'weather_limits' mapping for "
                        f"weather thresholds in activities {_format_ids(weather_alias_ids)}"
                    )

        resource_data = self._safe_load_mapping(resource_path, violations)
        if resource_data is not None:
            resources = resource_data.get("resources", [])
            if "resources" not in resource_data:
                violations.append("resource-plan.yaml: missing root key 'resources' as a list")
            elif not isinstance(resources, list):
                violations.append("resource-plan.yaml: 'resources' must be a list")
            if isinstance(resources, list):
                for idx, item in enumerate(resources):
                    if not isinstance(item, dict):
                        violations.append(f"resource-plan.yaml resources[{idx}]: expected mapping")
                        continue
                    resource_id = str(item.get("id", idx))
                    for field in ("id", "capacity", "daily_cost_cny"):
                        if field not in item:
                            violations.append(
                                f"resource-plan.yaml resources[{resource_id}]: missing required "
                                f"field '{field}'"
                            )

        contingency_data = self._safe_load_mapping(contingency_path, violations)
        if contingency_data is not None:
            root_aliases = (
                "contingency_policy",
                "contingency",
                "contingency_policies",
                "policies",
            )
            for alias in root_aliases:
                if "decisions" not in contingency_data and alias in contingency_data:
                    violations.append(
                        "contingency-policy.yaml: expected root key 'decisions' as a list; "
                        f"found '{alias}'"
                    )
            decisions = contingency_data.get("decisions", [])
            if "decisions" not in contingency_data:
                violations.append("contingency-policy.yaml: missing root key 'decisions' as a list")
            if isinstance(decisions, list):
                for idx, item in enumerate(decisions):
                    if not isinstance(item, dict):
                        violations.append(f"contingency-policy.yaml decisions[{idx}]: expected mapping")
                        continue
                    activity_id = str(item.get("activity_id", idx))
                    for field in ("activity_id", "decision", "params"):
                        if field not in item:
                            violations.append(
                                f"contingency-policy.yaml decisions[{activity_id}]: missing "
                                f"required field '{field}'"
                            )
                    if "params" in item and not isinstance(item.get("params"), dict):
                        violations.append(
                            f"contingency-policy.yaml decisions[{activity_id}].params: "
                            "expected mapping"
                        )
                    if "decision" not in item and "type" in item:
                        violations.append(
                            f"contingency-policy.yaml decision {activity_id}: expected "
                            "field 'decision'; found 'type'"
                        )
            elif decisions:
                violations.append("contingency-policy.yaml: 'decisions' must be a list")
        return violations

    def _safe_load_mapping(self, path: Path, comments: list[str]) -> dict[str, Any] | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            comments.append(f"{path.name}: YAML parse error - {exc}")
            return None
        except OSError as exc:
            comments.append(f"{path.name}: read error - {exc}")
            return None
        if not isinstance(data, dict):
            comments.append(f"{path.name}: expected mapping at root")
            return None
        return data


def _format_ids(ids: list[str], limit: int = 5) -> str:
    shown = ids[:limit]
    suffix = f", ... +{len(ids) - limit} more" if len(ids) > limit else ""
    return ", ".join(shown) + suffix
