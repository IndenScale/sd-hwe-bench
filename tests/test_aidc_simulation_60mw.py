"""Tests for 60MW AIDC simulation engine, LCC model, and new AIDC design tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from sd_hwe_bench.simulation.engine import AIDCSimulator, Strategy, StrategyDecision
from sd_hwe_bench.simulation.lifecycle import evaluate_lcc
from sd_hwe_bench.simulation.model import AIDCRoomModel, AIDCWeatherProfile
from sd_hwe_bench.simulation.strategy import make_baseline_strategy
from sd_hwe_bench.scorer import score_task
from sd_hwe_bench.task import TaskInstance


PROJECT_60MW = Path(__file__).parent.parent / "canonical" / "aidc-60mw"
TASK_EDGE = Path(__file__).parent.parent / "tasks" / "telecom" / "edge-dc-design-001"
TASK_CONCEPTUAL = Path(__file__).parent.parent / "tasks" / "telecom" / "aidc-60mw-001"
TASK_DETAILED = Path(__file__).parent.parent / "tasks" / "telecom" / "aidc-60mw-002"
TASK_EPC = Path(__file__).parent.parent / "tasks" / "telecom" / "aidc-60mw-003"


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


def test_task_edge_dc_design_solution_passes():
    """edge-dc-design-001 reference solution passes scoring."""
    task = TaskInstance(TASK_EDGE)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_EDGE / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert score.performance_score is not None
    # Regression: L4 weight must be counted once. A passing L4-replace task
    # tops out at exactly 1.0, not the old double-counted 1.15.
    assert score.overall_score == pytest.approx(1.0)


def test_task_conceptual_design_solution_passes():
    """aidc-60mw-001 (concept) reference solution passes scoring."""
    task = TaskInstance(TASK_CONCEPTUAL)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_CONCEPTUAL / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert score.performance_score is not None
    assert score.overall_score == pytest.approx(1.0)


def test_task_conceptual_design_scaffold_fails():
    """aidc-60mw-001 scaffold must not pass without agent outputs."""
    task = TaskInstance(TASK_CONCEPTUAL)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_CONCEPTUAL / "scaffold",
        task=task,
    )
    assert not score.success
    assert not score.layers["L0"].passed


def test_task_detailed_design_solution_passes():
    """aidc-60mw-002 (detailed) reference solution passes scoring."""
    task = TaskInstance(TASK_DETAILED)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_DETAILED / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert "L5" in score.layers
    assert score.layers["L5"].passed
    assert score.overall_score == pytest.approx(1.0)


def test_task_epc_solution_passes():
    """aidc-60mw-003 (epc) reference solution passes scoring."""
    task = TaskInstance(TASK_EPC)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=TASK_EPC / "solution",
        task=task,
    )
    assert score.success
    assert "L4" in score.layers
    assert score.layers["L4"].passed
    assert score.performance_score is not None
    assert score.overall_score == pytest.approx(1.0)


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
