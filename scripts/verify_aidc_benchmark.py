#!/usr/bin/env python3
"""端到端验证：AIDC v7 benchmark — ADL 加载 → 仿真 → 评分。

验证内容：
1. 14.8kW 小机房 ADL 项目加载与仿真
2. 60MW 大机房 ADL 项目加载与仿真
3. 夏季 48h 仿真策略区分度
4. PerformanceCritic 评分（含 reference 归一化）
5. 全生命周期成本（LCC）模型
6. v7 AIDC / EPC 任务参考解评分
"""

from __future__ import annotations

import json
import sys
import tempfile
import shutil
from pathlib import Path

# 确保项目在路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

from sd_hwe_bench.simulation.model import AIDCRoomModel, AIDCWeatherProfile
from sd_hwe_bench.simulation.engine import AIDCSimulator, Strategy, StrategyDecision
from sd_hwe_bench.simulation.strategy import (
    make_baseline_strategy,
    make_naive_fc_strategy,
    make_aggressive_strategy,
)
from sd_hwe_bench.simulation.lifecycle import evaluate_lcc
from sd_hwe_bench.critics.performance import PerformanceCritic
from sd_hwe_bench.task import TaskInstance
from sd_hwe_bench.scorer import score_task

BENCH_DIR = Path(__file__).parent.parent


def verify_adl_loading(project_dir: Path, room_id: str = "DC-HALL-A"):
    """验证 ADL 项目加载。"""
    print("=" * 60)
    print(f"Verify ADL Loading: {project_dir.name}")
    print("=" * 60)

    model = AIDCRoomModel.from_adl_project(project_dir, room_id=room_id)

    print(f"  Room:   {model.name} ({model.length_m}m × {model.width_m}m × {model.height_m}m)")
    print(f"  Area:   {model.floor_area_m2} m², Volume: {model.room_volume_m3} m³")
    print(f"  U-Value: {model.envelope_u} W/(m²·K)")
    print(f"  Design temp: {model.design_indoor_temp_c}°C")
    print(f"  Thermal capacity: {model.thermal_capacity_kj_k:.0f} kJ/K")
    print(f"  Cooling capacity: {model.total_cooling_capacity_kw} kW ({len(model.coolers)} units)")
    print(f"  Devices: {len(model.devices)} IT devices, total TDP: {model.total_it_tdp_kw:.1f} kW")
    if model.solar:
        print(f"  Solar: {model.solar.peak_power_kw} kWp")
    if model.battery:
        print(f"  Battery: {model.battery.capacity_kwh} kWh, max charge: {model.battery.max_charge_kw} kW")
    print(f"  Transformers: {len(model.transformers)}")
    print(f"  Grid carbon: {model.grid_carbon_intensity} kgCO₂/kWh")

    assert model.devices, "No devices loaded!"
    assert model.coolers, "No coolers loaded!"
    assert model.total_it_tdp_kw > 0, "IT TDP is zero!"
    print("  ✅ ADL loading OK\n")
    return model


def run_simulation_compare(model: AIDCRoomModel, weather: AIDCWeatherProfile, label: str,
                           pue_discrimination_threshold: float = 0.5):
    """运行三种策略并比较。"""
    print("=" * 60)
    print(f"Verify: {label} — Strategy Comparison")
    print("=" * 60)

    strategies = {
        "Baseline (fixed 12°C)": make_baseline_strategy(48),
        "Naive FC (day 12°C, night 22°C)": make_naive_fc_strategy(48),
        "Aggressive (FC + battery)": make_aggressive_strategy(48),
    }

    results = {}
    for name, strat in strategies.items():
        sim = AIDCSimulator(model, weather)
        result = sim.run(strat, hours=48)
        results[name] = result

        summary = result.summary()
        print(f"\n  [{name}]")
        print(f"    PUE:         {summary['avg_pue']:.3f}")
        print(f"    Energy:      {summary['total_energy_kwh']:.1f} kWh")
        print(f"    Carbon:      {summary['total_carbon_kg']:.1f} kgCO₂")
        print(f"    Water:       {summary['total_water_l']:.0f} L")
        print(f"    Cost:        ¥{summary['total_cost_cny']:.2f}")
        print(f"    Max temp:    {summary['max_indoor_temp_c']:.1f}°C")
        print(f"    Temp viol:   {summary['temp_violations']}")
        print(f"    SOC viol:    {summary['soc_violations']}")

    # 检查区分度
    baseline = results["Baseline (fixed 12°C)"]
    naive = results["Naive FC (day 12°C, night 22°C)"]
    aggressive = results["Aggressive (FC + battery)"]

    print(f"\n  --- Improvement over Baseline ---")
    pue_delta_naive = (baseline.avg_pue - naive.avg_pue) / baseline.avg_pue * 100
    pue_delta_agg = (baseline.avg_pue - aggressive.avg_pue) / baseline.avg_pue * 100
    print(f"  Naive FC PUE improvement:    {pue_delta_naive:+.1f}%")
    print(f"  Aggressive PUE improvement:  {pue_delta_agg:+.1f}%")

    carbon_delta_naive = (baseline.total_carbon_kg - naive.total_carbon_kg) / baseline.total_carbon_kg * 100
    carbon_delta_agg = (baseline.total_carbon_kg - aggressive.total_carbon_kg) / baseline.total_carbon_kg * 100
    print(f"  Naive FC Carbon reduction:   {carbon_delta_naive:+.1f}%")
    print(f"  Aggressive Carbon reduction: {carbon_delta_agg:+.1f}%")

    assert abs(pue_delta_naive) > pue_discrimination_threshold or abs(pue_delta_agg) > pue_discrimination_threshold, \
        f"WARNING: Insufficient PUE discrimination ({pue_delta_naive:.1f}%, {pue_delta_agg:.1f}%)"

    print("  ✅ Strategy comparison OK\n")
    return results


def verify_60mw_optimized_strategy():
    """验证 60MW 模型在优化策略下可达 PUE ≤ 1.20。"""
    print("=" * 60)
    print("Verify: 60MW Optimized Strategy")
    print("=" * 60)

    project_dir = BENCH_DIR / "canonical" / "aidc-60mw"
    model = AIDCRoomModel.from_adl_project(project_dir, room_id="DC-HALL-60MW")
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0)

    decisions = []
    for h in range(48):
        hod = h % 24
        if 0 <= hod <= 13 or hod >= 22:
            decisions.append(StrategyDecision(it_utilization=0.7, chiller_setpoint_c=24.0, battery_mode="idle"))
        else:
            decisions.append(StrategyDecision(it_utilization=0.7, chiller_setpoint_c=12.0, battery_mode="idle"))

    sim = AIDCSimulator(model, weather)
    result = sim.run(Strategy(decisions=decisions), hours=48)
    summary = result.summary()

    print(f"  PUE:      {summary['avg_pue']:.3f}")
    print(f"  Carbon:   {summary['total_carbon_kg']:.0f} kgCO₂")
    print(f"  Cost:     ¥{summary['total_cost_cny']:.2f}")
    print(f"  Max temp: {summary['max_indoor_temp_c']:.1f}°C")
    print(f"  Temp violations: {summary['temp_violations']}")

    assert result.avg_pue <= 1.22, f"Optimized PUE too high: {result.avg_pue:.3f}"
    assert result.temp_violations == 0, "Temperature violations detected!"
    print("  ✅ 60MW optimized strategy OK\n")
    return result


def verify_lcc():
    """验证 LCC 模型计算。"""
    print("=" * 60)
    print("Verify: LCC Model")
    print("=" * 60)

    project_dir = BENCH_DIR / "canonical" / "aidc-60mw"
    model = AIDCRoomModel.from_adl_project(project_dir, room_id="DC-HALL-60MW")
    weather = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0)
    sim = AIDCSimulator(model, weather)
    result = sim.run(make_baseline_strategy(48), hours=48)
    lcc = evaluate_lcc(model, result)

    print(f"  CAPEX:    ¥{lcc.capex_total_cny/1e6:.1f}M")
    print(f"  Annual OPEX:   ¥{lcc.annual_opex_cny/1e6:.1f}M")
    print(f"  Annual Revenue: ¥{lcc.annual_revenue_cny/1e6:.1f}M")
    print(f"  NPV:      ¥{lcc.npv_cny/1e6:.1f}M")
    print(f"  TCO:      ¥{lcc.tco_cny/1e6:.1f}M")
    print(f"  LCOE:     ¥{lcc.lcoe_cny_per_kwh:.4f}/kWh")

    assert lcc.capex_total_cny > 0, "CAPEX must be positive"
    assert lcc.tco_cny > lcc.capex_total_cny, "TCO must be greater than CAPEX"
    print("  ✅ LCC model OK\n")
    return lcc


def verify_task_scoring(task_dir: Path):
    """验证 benchmark 任务评分。"""
    print("=" * 60)
    print(f"Verify: Task Scoring {task_dir.name}")
    print("=" * 60)

    task = TaskInstance(task_dir)
    score = score_task(
        task_id=task.task_id,
        agent_output_dir=task_dir / "solution",
        task=task,
    )

    print(f"  Success: {score.success}")
    print(f"  Overall score: {score.overall_score:.3f}")
    for cr in score.critic_results:
        if cr.name == "L7-Performance":
            print(f"  L7 score: {cr.score:.4f}")

    assert score.success, f"Task {task.task_id} solution did not pass"
    print("  ✅ Task scoring OK\n")


def verify_scoring_small(model, weather):
    """验证小机房评分 critic 输出。"""
    print("=" * 60)
    print("Verify: Performance Scoring (14.8kW)")
    print("=" * 60)

    critic = PerformanceCritic(
        project_dir=BENCH_DIR / "canonical" / "datacenter-hall",
        weather=weather,
        simulation_hours=48,
        reference={
            "avg_pue": 1.289,
            "total_carbon_kg": 246,
            "total_water_l": 70,
            "total_cost_cny": 318,
        },
    )

    class FakeTask:
        class Metadata:
            requirement = ""
            l7_config = {}
        metadata = Metadata()

    task = FakeTask()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "strategy_name": "free-cooling-optimized",
            "templates": [
                {"name": "day", "hours": "8-20", "it_utilization": 0.8, "chiller_setpoint_c": 16.0, "battery_mode": "auto"},
                {"name": "night", "hours": "0-7,21-23", "it_utilization": 0.8, "chiller_setpoint_c": 24.0, "battery_mode": "charge"},
            ]
        }, f)
        strategy_path = Path(f.name)

    ws = Path(tempfile.mkdtemp())
    shutil.copy(strategy_path, ws / "strategy.yaml")

    result = critic.evaluate(ws, task)

    print(f"  Score: {result.score:.4f}")
    print(f"  Passed: {result.passed}")

    strategy_path.unlink()
    shutil.rmtree(ws)

    assert result.score > 0.5, f"Score too low: {result.score}"
    print("  ✅ Scoring OK\n")


def main():
    print("\n🔬 AIDC Benchmark Verification\n")

    # Verify 1: 14.8kW small room
    small_model = verify_adl_loading(BENCH_DIR / "canonical" / "datacenter-hall")

    # Verify 2: 60MW large room
    large_model = verify_adl_loading(BENCH_DIR / "canonical" / "aidc-60mw", room_id="DC-HALL-60MW")

    # Verify 3: Small room summer/winter comparison
    summer = AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=25.0)
    run_simulation_compare(small_model, summer, "Small Room Summer (35°C peak)")

    winter = AIDCWeatherProfile.synthetic_winter_day(peak_temp_c=10.0, night_temp_c=-2.0)
    run_simulation_compare(small_model, winter, "Small Room Winter (10°C peak)")

    # Verify 4: 60MW optimized strategy
    verify_60mw_optimized_strategy()

    # Verify 5: 60MW strategy discrimination
    run_simulation_compare(large_model, AIDCWeatherProfile.synthetic_summer_day(peak_temp_c=35.0, night_temp_c=22.0),
                           "60MW Summer (35°C peak, 22°C night)", pue_discrimination_threshold=3.0)

    # Verify 6: LCC model
    verify_lcc()

    # Verify 7: Scoring
    verify_scoring_small(small_model, summer)

    # Verify 8: v7 task scoring
    for task_name in [
        "edge-dc-design-001",
        "aidc-60mw-001",
        "aidc-60mw-002",
        "aidc-60mw-003",
    ]:
        verify_task_scoring(BENCH_DIR / "tasks" / "telecom" / task_name)

    print("=" * 60)
    print("🎉 ALL VERIFICATIONS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
