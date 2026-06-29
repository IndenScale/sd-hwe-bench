"""Evaluate a simulated construction schedule."""

from __future__ import annotations

from sd_hwe_bench.construction.cpml import ResourcePlan, Schedule
from sd_hwe_bench.construction.scheduler import SimulationResult


def evaluate_schedule(
    simulation_result: SimulationResult,
    resource_plan: ResourcePlan,
    schedule: Schedule,
    deadline_days: int = 180,
    reference_cost_cny: float | None = None,
) -> dict:
    """Compute schedule cost and SLA metrics."""
    resource_cost_per_day = {
        r.id: r.daily_cost_cny * r.total_capacity for r in resource_plan.resources
    }

    # Daily active cost = sum of requested resources * daily cost.
    active_cost = 0.0
    for times in simulation_result.activity_times.values():
        start, end = times
        for d in range(start, end):
            if d >= len(simulation_result.resource_usage):
                break
            for rid, used in simulation_result.resource_usage[d].items():
                active_cost += used * resource_cost_per_day.get(rid, 0.0)

    # Total committed resource cost over makespan.
    makespan = simulation_result.makespan_days
    total_committed_cost = sum(resource_cost_per_day.values()) * max(makespan, 1)
    idle_cost = total_committed_cost - active_cost
    idle_cost = max(0.0, idle_cost)

    sla_met = makespan > 0 and makespan <= deadline_days and simulation_result.all_scheduled
    cost_overrun_ratio = None
    if reference_cost_cny:
        cost_overrun_ratio = (total_committed_cost - reference_cost_cny) / reference_cost_cny

    return {
        "makespan_days": makespan,
        "total_cost_cny": round(total_committed_cost, 2),
        "resource_idle_cost_cny": round(idle_cost, 2),
        "sla_met": sla_met,
        "cost_overrun_ratio": (
            round(cost_overrun_ratio, 4) if cost_overrun_ratio is not None else None
        ),
    }
