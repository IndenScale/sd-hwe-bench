"""全生命周期成本（LCC）模型 — CAPEX + OPEX + 时间价值。

用于 AIDC co-design 任务：Agent 同时优化物理设计与运营策略时，
不仅看 48h 运营指标，还要看 15 年 NPV / TCO。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sd_hwe_bench.simulation.engine import SimulationResult
from sd_hwe_bench.simulation.model import AIDCRoomModel


@dataclass
class LCCResult:
    """LCC 计算结果。"""

    capex_total_cny: float = 0.0
    annual_opex_cny: float = 0.0
    annual_revenue_cny: float = 0.0
    annual_net_cny: float = 0.0
    npv_cny: float = 0.0
    tco_cny: float = 0.0
    lcoe_cny_per_kwh: float = 0.0

    def summary(self) -> dict:
        return {
            "capex_total_m_cny": round(self.capex_total_cny / 1e6, 2),
            "annual_opex_m_cny": round(self.annual_opex_cny / 1e6, 2),
            "annual_revenue_m_cny": round(self.annual_revenue_cny / 1e6, 2),
            "annual_net_m_cny": round(self.annual_net_cny / 1e6, 2),
            "npv_m_cny": round(self.npv_cny / 1e6, 2),
            "tco_m_cny": round(self.tco_cny / 1e6, 2),
            "lcoe_cny_per_kwh": round(self.lcoe_cny_per_kwh, 4),
        }


class LCCEvaluator:
    """从 AIDC 房间模型和 48h 仿真结果计算 LCC。"""

    # 默认运行小时数/年（考虑维护、扩容等）
    ANNUAL_OPERATION_HOURS: float = 8760.0 * 0.95  # 95% 可用率

    def __init__(self, model: AIDCRoomModel, result: SimulationResult,
                 lifetime_years: Optional[int] = None,
                 discount_rate: Optional[float] = None):
        self.model = model
        self.result = result
        self.lifetime = lifetime_years or model.lifecycle.project_lifetime_years
        self.discount_rate = discount_rate or model.lifecycle.discount_rate
        self.cfg = model.lifecycle

    def evaluate(self) -> LCCResult:
        """计算完整 LCC。"""
        capex = self._compute_capex()
        annual_opex = self._compute_annual_opex()
        annual_revenue = self._compute_annual_revenue()
        annual_net = annual_opex - annual_revenue  # 净现金流出（正值为成本）

        npv = capex
        for year in range(1, self.lifetime + 1):
            npv += annual_net / ((1 + self.discount_rate) ** year)

        tco = capex + annual_opex * self.lifetime

        # 平准化电力成本（元/kWh）：总成本 / 总发电量（IT 能量）
        total_it_kwh_annual = self._annual_it_energy_kwh()
        lcoe = tco / (total_it_kwh_annual * self.lifetime) if total_it_kwh_annual > 0 else 0.0

        return LCCResult(
            capex_total_cny=capex,
            annual_opex_cny=annual_opex,
            annual_revenue_cny=annual_revenue,
            annual_net_cny=annual_net,
            npv_cny=npv,
            tco_cny=tco,
            lcoe_cny_per_kwh=lcoe,
        )

    def _compute_capex(self) -> float:
        """计算建设期 CAPEX。"""
        cfg = self.cfg
        m = self.model
        capex = 0.0

        # 1. 冷却系统
        if m.cooling_architecture in ("liquid-cooled", "hybrid"):
            # 液冷：CDU + 冷却塔
            cdu_capacity_kw = m.total_cooling_capacity_kw
            capex += cdu_capacity_kw * cfg.cdu_cny_per_kw
            capex += cdu_capacity_kw * cfg.cooling_tower_cny_per_kw
        else:
            # 风冷：冷水机组 + 冷却塔
            capex += m.total_cooling_capacity_kw * cfg.chiller_cny_per_kw
            capex += m.total_cooling_capacity_kw * cfg.cooling_tower_cny_per_kw

        # 2. 变压器
        for tr in m.transformers:
            capex += tr.capacity_mva * cfg.transformer_cny_per_mva

        # 3. 储能
        if m.battery:
            capex += m.battery.capacity_kwh * cfg.battery_cny_per_kwh

        # 4. 光伏
        if m.solar:
            capex += m.solar.peak_power_kw * cfg.solar_cny_per_kwp

        # 5. 机柜（从 instances/racks 统计，若不存在则按 200 台估算）
        rack_count = self._count_racks()
        capex += rack_count * cfg.rack_cny_per_unit

        # 6. 土建
        capex += m.floor_area_m2 * cfg.civil_cny_per_m2

        # 7. UPS（按 IT 负载 10% 配置，简化）
        ups_kw = m.total_it_tdp_kw * 0.1
        capex += ups_kw * cfg.ups_cny_per_kw

        return capex

    def _compute_annual_opex(self) -> float:
        """计算年度 OPEX。"""
        cfg = self.cfg
        m = self.model

        # 1. 电费：从 48h 仿真结果外推到全年
        # 48h 电费 / 48 * 全年运行小时
        electricity_cost_annual = self.result.total_cost_cny / 48.0 * self.ANNUAL_OPERATION_HOURS

        # 2. 水费
        water_cost_annual = (
            self.result.total_water_l / 1000.0 / 48.0 * self.ANNUAL_OPERATION_HOURS * cfg.water_price_cny_per_m3
        )

        # 3. 维护费
        capex = self._compute_capex()
        maintenance_annual = (
            m.total_cooling_capacity_kw * cfg.chiller_cny_per_kw * cfg.cooling_opex_rate
            + sum(tr.capacity_mva * cfg.transformer_cny_per_mva for tr in m.transformers) * cfg.electrical_opex_rate
        )
        if m.battery:
            maintenance_annual += m.battery.capacity_kwh * cfg.battery_cny_per_kwh * cfg.battery_opex_rate
        if m.solar:
            maintenance_annual += m.solar.peak_power_kw * cfg.solar_cny_per_kwp * cfg.solar_opex_rate

        return electricity_cost_annual + water_cost_annual + maintenance_annual

    def _compute_annual_revenue(self) -> float:
        """计算年度 IT 负载租金收益（早投产价值）。"""
        cfg = self.cfg
        m = self.model
        # 按实际平均 IT 功率（而非 TDP）计算
        avg_it_power_kw = sum(s.it_power_kw for s in self.result.snapshots) / max(1, len(self.result.snapshots))
        return avg_it_power_kw * cfg.it_revenue_cny_per_kw_year

    def _annual_it_energy_kwh(self) -> float:
        """年度 IT 耗电量（kWh）。"""
        avg_it_power_kw = sum(s.it_power_kw for s in self.result.snapshots) / max(1, len(self.result.snapshots))
        return avg_it_power_kw * self.ANNUAL_OPERATION_HOURS

    def _count_racks(self) -> int:
        """统计 instances/racks 下的机柜数量。"""
        racks_dir = Path(self.model.room_id)
        # 实际 model 不保存 project_dir，这里从 room_id 无法直接得到路径。
        # 简单按房间面积和功率密度反推：单机柜 30kW。
        if self.model.total_it_tdp_kw > 0:
            return max(1, int(self.model.total_it_tdp_kw / 30.0))
        return 200


def evaluate_lcc(model: AIDCRoomModel, result: SimulationResult,
                 lifetime_years: Optional[int] = None,
                 discount_rate: Optional[float] = None) -> LCCResult:
    """便捷函数：计算 LCC。"""
    return LCCEvaluator(model, result, lifetime_years, discount_rate).evaluate()
