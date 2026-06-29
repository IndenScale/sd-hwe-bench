"""CPML (Construction Project Modeling Language) dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Activity:
    """A construction activity."""

    id: str
    name: str
    duration_days: int
    resource_requests: dict[str, float] = field(default_factory=dict)
    predecessors: list[str] = field(default_factory=list)
    is_outdoor: bool = False
    weather_delay_thresholds: dict[str, float] = field(default_factory=dict)


@dataclass
class Resource:
    """A renewable construction resource."""

    id: str
    name: str
    total_capacity: float
    daily_cost_cny: float


@dataclass
class Precedence:
    """A finish-to-start precedence relation with optional lag."""

    from_id: str
    to_id: str
    lag_days: int = 0


@dataclass
class WeatherWindow:
    """Daily weather conditions."""

    day: int
    wind_m_s: float
    rain_mm_h: float


@dataclass
class SupplyDelay:
    """A stochastic supply delay affecting an activity."""

    activity_id: str
    delay_days: int


@dataclass
class ContingencyDecision:
    """A contingency decision applied to an activity."""

    activity_id: str
    decision_type: str  # "wait", "defer-shipment", "skip-to-later"
    params: dict = field(default_factory=dict)


@dataclass
class Schedule:
    """A construction master schedule."""

    activities: list[Activity] = field(default_factory=list)
    precedences: list[Precedence] = field(default_factory=list)


@dataclass
class ResourcePlan:
    """A resource plan."""

    resources: list[Resource] = field(default_factory=list)


@dataclass
class ContingencyPolicy:
    """A contingency policy."""

    decisions: list[ContingencyDecision] = field(default_factory=list)
