"""EPC (Engineering, Procurement, Construction) critic for AIDC tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
