"""Tests for 60MW AIDC simulation engine, LCC model, and new benchmark tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from sd_hwe_bench.simulation.engine import AIDCSimulator, Strategy, StrategyDecision
from sd_hwe_bench.simulation.lifecycle import evaluate_lcc
from sd_hwe_bench.simulation.model import AIDCRoomModel, AIDCWeatherProfile
from sd_hwe_bench.simulation.strategy import make_baseline_strategy
from sd_hwe_bench.scorer import score_task
from sd_hwe_bench.task import TaskInstance


PROJECT_60MW = Path(__file__).parent.parent / "canonical" / "datacenter-hall-60mw"
TASK_OPERATION = Path(__file__).parent.parent / "tasks" / "telecom" / "aidc-operation-002"
TASK_CODesign = Path(__file__).parent.parent / "tasks" / "telecom" / "aidc-co-design-002"


def test_60mw_adl_loading():
    """60MW canonical project loads correctly."""
    model = AIDCRoomModel.from_adl_project(PROJECT_60MW, room_id="DC-HALL-60MW")
    assert model.total_it_tdp_kw == pytest.approx(60000.0, rel=1e-6)
    assert len(model.coolers) == 8
    assert model.total_cooling_capacity_kw == pytest.approx(80000.0, rel=1e-6)
    assert model.solar is not None
    assert model.solar.peak_power_kw == pytest.approx(5000.0, rel=1e-6)
    assert model.battery is not None
    assert model.battery.capacity_kwh == pytest.approx(20000.0, rel=1e-6)
    assert len(model.transformers) == 2


def test_60mw_baseline_simulation():
    """Baseline simulation for 60MW model runs without violations."""
    model = AIDCRoomModel.from_adl_project(PROJECT_60MW, room_id="DC-HALL-60MW")
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0)
    sim = AIDCSimulator(model, weather)
    result = sim.run(make_baseline_strategy(48), hours=48)

    assert result.temp_violations == 0
    assert result.soc_violations == 0
    assert 1.0 < result.avg_pue < 1.5


def test_60mw_optimized_strategy_pue():
    """Optimized strategy improves PUE by at least 5%."""
    model = AIDCRoomModel.from_adl_project(PROJECT_60MW, room_id="DC-HALL-60MW")
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0)

    baseline = AIDCSimulator(model, weather).run(make_baseline_strategy(48), hours=48)

    decisions = []
    for h in range(48):
        hod = h % 24
        if 0 <= hod <= 13 or hod >= 22:
            decisions.append(StrategyDecision(it_utilization=0.7, chiller_setpoint_c=24.0, battery_mode="idle"))
        else:
            decisions.append(StrategyDecision(it_utilization=0.7, chiller_setpoint_c=12.0, battery_mode="idle"))

    optimized = AIDCSimulator(model, weather).run(Strategy(decisions=decisions), hours=48)

    assert optimized.avg_pue <= 1.22
    pue_improvement = (baseline.avg_pue - optimized.avg_pue) / baseline.avg_pue
    assert pue_improvement >= 0.05, f"PUE improvement only {pue_improvement:.2%}"


def test_lcc_model_positive():
    """LCC model returns positive CAPEX and TCO > CAPEX."""
    model = AIDCRoomModel.from_adl_project(PROJECT_60MW, room_id="DC-HALL-60MW")
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0)
    sim = AIDCSimulator(model, weather)
    result = sim.run(make_baseline_strategy(48), hours=48)
    lcc = evaluate_lcc(model, result)

    assert lcc.capex_total_cny > 0
    assert lcc.tco_cny > lcc.capex_total_cny
    assert lcc.lcoe_cny_per_kwh > 0


def test_task_operation_002_solution_passes():
    """aidc-operation-002 reference solution passes scoring."""
    task = TaskInstance(TASK_OPERATION)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_OPERATION / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert score.performance_score is not None


def test_task_co_design_002_solution_passes():
    """aidc-co-design-002 reference solution passes scoring."""
    task = TaskInstance(TASK_CODesign)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_CODesign / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert score.performance_score is not None


def test_weather_wet_bulb_calculation():
    """Synthetic weather includes wet-bulb temperatures."""
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=25.0)
    for point in weather.points:
        assert point.wet_bulb_temp_c <= point.temp_c
        assert point.wet_bulb_temp_c > -10.0


def test_transformer_efficiency_model():
    """Transformer efficiency varies with load ratio."""
    model = AIDCRoomModel.from_adl_project(PROJECT_60MW, room_id="DC-HALL-60MW")
    tr = model.transformers[0]
    eff_low = tr.efficiency_at_load(0.1)
    eff_mid = tr.efficiency_at_load(0.5)
    eff_high = tr.efficiency_at_load(1.0)
    assert 0.9 < eff_low <= 1.0
    assert 0.9 < eff_high <= 1.0
    assert eff_mid >= eff_low
