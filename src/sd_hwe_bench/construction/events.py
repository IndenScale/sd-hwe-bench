"""Scenario generation for construction scheduling."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from sd_hwe_bench.construction.cpml import Activity, SupplyDelay, WeatherWindow


def _summer_wind(day: int) -> float:
    """Deterministic summer wind profile with occasional storm days."""
    base = 4.0 + 3.0 * math.sin(day / 30.0)
    storm = 12.0 if day % 23 == 7 else 0.0
    return base + storm + 2.0 * math.sin(day * 0.7)


def _summer_rain(day: int) -> float:
    """Deterministic summer rain profile with occasional heavy rain."""
    base = 0.5 + 1.5 * math.sin(day / 18.0)
    shower = 8.0 if day % 17 == 3 else 0.0
    return max(0.0, base + shower + math.sin(day * 0.9))


def generate_weather_profile(days: int = 180) -> list[WeatherWindow]:
    """Generate a deterministic summer weather profile."""
    return [
        WeatherWindow(
            day=d,
            wind_m_s=round(_summer_wind(d), 2),
            rain_mm_h=round(_summer_rain(d), 2),
        )
        for d in range(days)
    ]


def generate_supply_delays(activities: list[Activity], seed: int = 0) -> list[SupplyDelay]:
    """Randomly delay a few activities by 1-14 days."""
    rng = random.Random(seed)
    delays = []
    if not activities:
        return delays
    n_delays = rng.randint(1, max(1, len(activities) // 5))
    chosen = rng.sample(activities, min(n_delays, len(activities)))
    for activity in chosen:
        delays.append(
            SupplyDelay(
                activity_id=activity.id,
                delay_days=rng.randint(1, 14),
            )
        )
    return delays


@dataclass
class Scenario:
    """A stochastic construction scenario."""

    weather: list[WeatherWindow] = field(default_factory=list)
    supply_delays: list[SupplyDelay] = field(default_factory=list)


def generate_scenarios(n: int = 30, horizon_days: int = 180) -> list[Scenario]:
    """Generate N stochastic scenarios."""
    base_weather = generate_weather_profile(horizon_days)
    scenarios = []
    for seed in range(n):
        weather = [
            WeatherWindow(
                day=w.day,
                wind_m_s=round(
                    w.wind_m_s + random.Random(seed + w.day).uniform(-2, 2), 2
                ),
                rain_mm_h=round(
                    max(
                        0.0,
                        w.rain_mm_h
                        + random.Random(seed * 7 + w.day).uniform(-1, 3),
                    ),
                    2,
                ),
            )
            for w in base_weather
        ]
        scenarios.append(Scenario(weather=weather, supply_delays=[]))
    return scenarios
