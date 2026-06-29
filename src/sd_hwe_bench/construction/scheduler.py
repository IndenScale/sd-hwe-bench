"""Discrete-event scheduler for CPML construction models."""

from __future__ import annotations

from dataclasses import dataclass

from sd_hwe_bench.construction.cpml import (
    Activity,
    ContingencyPolicy,
    Resource,
    ResourcePlan,
    Schedule,
    SupplyDelay,
    WeatherWindow,
)


@dataclass
class SimulationResult:
    """Result of a schedule simulation."""

    makespan_days: int
    activity_times: dict[str, tuple[int, int]]
    resource_usage: list[dict[str, float]]
    violations: list[str]
    all_scheduled: bool


def _weather_ok(
    day: int,
    duration: int,
    weather: list[WeatherWindow],
    thresholds: dict[str, float],
) -> bool:
    """Check if an activity can be performed starting at day."""
    if not thresholds or not weather:
        return True
    wind_limit = thresholds.get("wind_m_s", float("inf"))
    rain_limit = thresholds.get("rain_mm_h", float("inf"))
    for d in range(day, day + duration):
        if d >= len(weather):
            return False
        window = weather[d]
        if window.wind_m_s > wind_limit or window.rain_mm_h > rain_limit:
            return False
    return True


def _resources_available(
    day: int,
    duration: int,
    activity: Activity,
    resource_usage: list[dict[str, float]],
    resources: list[Resource],
) -> bool:
    """Check if resources are available for the activity window."""
    capacity = {r.id: r.total_capacity for r in resources}
    for d in range(day, day + duration):
        if d >= len(resource_usage):
            continue
        for rid, req in activity.resource_requests.items():
            if resource_usage[d].get(rid, 0.0) + req > capacity.get(rid, 0.0):
                return False
    return True


def _allocate_resources(
    day: int,
    duration: int,
    activity: Activity,
    resource_usage: list[dict[str, float]],
    horizon_days: int,
) -> None:
    """Allocate activity resources to the usage grid."""
    for d in range(day, day + duration):
        if d >= horizon_days:
            break
        if d >= len(resource_usage):
            resource_usage.extend([{} for _ in range(len(resource_usage), d + 1)])
        for rid, req in activity.resource_requests.items():
            resource_usage[d][rid] = resource_usage[d].get(rid, 0.0) + req


def _apply_contingency(
    activity: Activity,
    policy: ContingencyPolicy,
    earliest_start: int,
) -> int:
    """Apply contingency decision to earliest start."""
    for decision in policy.decisions:
        if decision.activity_id != activity.id:
            continue
        if decision.decision_type == "wait":
            return earliest_start
        if decision.decision_type == "defer-shipment":
            return earliest_start + int(decision.params.get("delay_days", 0))
        if decision.decision_type == "skip-to-later":
            return max(earliest_start, int(decision.params.get("start_after_day", 0)))
    return earliest_start


def run_schedule(
    schedule: Schedule,
    resource_plan: ResourcePlan,
    weather: list[WeatherWindow],
    supply_delays: list[SupplyDelay],
    contingency_policy: ContingencyPolicy,
    horizon_days: int = 180,
) -> SimulationResult:
    """Run a forward list-scheduling simulation."""
    activities = {a.id: a for a in schedule.activities}
    resources = resource_plan.resources
    resource_usage: list[dict[str, float]] = [{} for _ in range(horizon_days)]
    activity_times: dict[str, tuple[int, int]] = {}
    violations: list[str] = []

    delay_map = {d.activity_id: d.delay_days for d in supply_delays}
    remaining = set(activities.keys())
    scheduled = set()

    # Iteratively schedule activities whose predecessors are done.
    while remaining:
        ready = []
        for aid in remaining:
            activity = activities[aid]
            preds_done = all(p in scheduled for p in activity.predecessors)
            if preds_done:
                ready.append(aid)

        if not ready:
            # Cyclic or unsatisfiable precedence; report and stop.
            violations.append(f"Precedence deadlock: cannot schedule {remaining}")
            break

        for aid in ready:
            activity = activities[aid]
            # Earliest start from predecessors + lag + supply delay.
            earliest = 0
            for prec in schedule.precedences:
                if prec.to_id == aid and prec.from_id in activity_times:
                    finish = activity_times[prec.from_id][1]
                    earliest = max(earliest, finish + prec.lag_days)
            earliest += delay_map.get(aid, 0)

            # Apply contingency decision.
            earliest = _apply_contingency(activity, contingency_policy, earliest)

            # Find feasible start day respecting weather and resources.
            start = earliest
            scheduled_ok = False
            while start + activity.duration_days <= horizon_days:
                if activity.is_outdoor and not _weather_ok(
                    start, activity.duration_days, weather, activity.weather_delay_thresholds
                ):
                    start += 1
                    continue
                if not _resources_available(
                    start, activity.duration_days, activity, resource_usage, resources
                ):
                    start += 1
                    continue
                _allocate_resources(
                    start, activity.duration_days, activity, resource_usage, horizon_days
                )
                activity_times[aid] = (start, start + activity.duration_days)
                scheduled.add(aid)
                scheduled_ok = True
                break

            if not scheduled_ok:
                violations.append(
                    f"Activity {aid} cannot be scheduled within {horizon_days} days"
                )
                scheduled.add(aid)  # avoid infinite loop

        remaining -= scheduled

    # Check resource capacity violations (defensive).
    capacity = {r.id: r.total_capacity for r in resources}
    for d, usage in enumerate(resource_usage):
        for rid, used in usage.items():
            cap = capacity.get(rid, 0.0)
            if used > cap + 1e-9:
                violations.append(
                    f"Day {d}: resource {rid} over capacity ({used:.2f} > {cap:.2f})"
                )

    all_scheduled = len(activity_times) == len(activities) and not any(
        "cannot be scheduled" in v for v in violations
    )
    makespan = max((end for _, end in activity_times.values()), default=0)

    return SimulationResult(
        makespan_days=makespan,
        activity_times=activity_times,
        resource_usage=resource_usage,
        violations=violations,
        all_scheduled=all_scheduled,
    )
