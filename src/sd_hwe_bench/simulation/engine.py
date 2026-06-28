"""AIDC 运营仿真引擎 — 每小时步进的 RC 热网络 + 电力调度 + 碳/水核算。

架构：
  运营策略 (Strategy) → 仿真引擎 (AIDCSimulator) → 时间序列结果 (SimulationResult)

热模型：简化为单节点 RC 网络（集总参数）
  dT/dt = (Q_it + Q_solar + Q_envelope - Q_cooling) / C_thermal
  Q_envelope = U * A * (T_outdoor - T_indoor)
  Q_cooling = 冷却机组实际制冷量

电力拓扑：
  P_grid + P_solar + P_battery = P_it + P_cooling + P_pump + P_mechanical + P_transformer_loss
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from sd_hwe_bench.simulation.model import (
    AIDCRoomModel,
    AIDCWeatherProfile,
    BatterySpec,
)


@dataclass
class HourlySnapshot:
    """单小时的仿真状态快照。"""

    hour: int
    # 输入
    outdoor_temp_c: float
    solar_irradiance_w_m2: float
    it_utilization: float           # Agent 指定的 IT 负载率
    chiller_setpoint_c: float       # Agent 指定的冷冻水温度设定点
    # 中间计算
    it_power_kw: float
    it_heat_kw: float               # IT 散热量（≈ IT 功耗）
    solar_output_kw: float
    battery_soc_kwh: float
    battery_charge_kw: float        # +充电, -放电
    grid_power_kw: float
    indoor_temp_c: float            # 本小时结束时的室内温度
    cooling_load_kw: float          # 实际冷负荷
    cooling_power_kw: float         # 冷却系统功耗
    pump_power_kw: float            # 液冷泵功耗
    mechanical_power_kw: float      # 机械系统功耗（不含冷却）
    transformer_loss_kw: float      # 变压器损耗
    free_cooling_active: bool
    cop_actual: float
    transformer_efficiency: float
    # 输出指标
    total_power_kw: float           # 总输入功率
    pue: float
    carbon_kg: float                # 本小时碳排放
    water_consumption_l: float      # 本小时水消耗
    cost_cny: float                 # 本小时电费


@dataclass
class SimulationResult:
    """完整仿真结果。"""

    snapshots: list[HourlySnapshot] = field(default_factory=list)
    # 总计
    total_energy_kwh: float = 0.0
    total_carbon_kg: float = 0.0
    total_water_l: float = 0.0
    total_cost_cny: float = 0.0
    avg_pue: float = 0.0
    max_indoor_temp_c: float = 0.0
    # 约束违反
    temp_violations: int = 0         # 温度超限次数
    soc_violations: int = 0          # SOC 过低次数

    def summary(self) -> dict:
        return {
            "hours": len(self.snapshots),
            "total_energy_kwh": round(self.total_energy_kwh, 1),
            "total_carbon_kg": round(self.total_carbon_kg, 1),
            "total_water_l": round(self.total_water_l, 0),
            "total_cost_cny": round(self.total_cost_cny, 2),
            "avg_pue": round(self.avg_pue, 3),
            "max_indoor_temp_c": round(self.max_indoor_temp_c, 1),
            "temp_violations": self.temp_violations,
            "soc_violations": self.soc_violations,
        }


@dataclass
class Strategy:
    """Agent 产出的运营策略。

    每小时一个决策点。如果小时数小于仿真时长则循环使用。
    """

    decisions: list[StrategyDecision] = field(default_factory=list)

    def get(self, hour: int) -> "StrategyDecision":
        if not self.decisions:
            return StrategyDecision()
        return self.decisions[hour % len(self.decisions)]


@dataclass
class StrategyDecision:
    """单小时的运营决策。"""

    it_utilization: float = 0.7        # IT 负载率 [0, 1]，仅影响 power，不模拟实际计算
    chiller_setpoint_c: float = 12.0   # 冷冻水温度设定点 ℃
    battery_mode: str = "auto"         # "charge" | "discharge" | "idle" | "auto"
    load_shedding: bool = False        # 是否削减非关键负载


class AIDCSimulator:
    """AIDC 运营仿真引擎。

    使用方式：
        model = AIDCRoomModel.from_adl_project(Path("canonical/datacenter-hall"))
        weather = AIDCWeatherProfile.synthetic_summer_day()
        strategy = Strategy(decisions=[...])
        sim = AIDCSimulator(model, weather)
        result = sim.run(strategy)
    """

    # 仿真常量
    TIME_STEP_H: float = 1.0          # 时间步长（小时）
    MAX_INDOOR_TEMP_C: float = 32.0    # 最高允许室内温度
    COP_REFERENCE_SETPOINT_C: float = 12.0  # COP 参考设定点
    COP_SETPOINT_PENALTY_PER_C: float = 0.10  # 每偏离 1°C 的 COP 相对变化
    LIQUID_PUMP_W_PER_KW_LOAD: float = 0.015  # 液冷泵功耗：冷却负荷的 1.5%
    LIQUID_PUMP_HEAD_FACTOR: float = 0.008    # 风冷泵/风机额外功耗因子

    def __init__(self, model: AIDCRoomModel, weather: AIDCWeatherProfile,
                 electricity_price: float | None = None):
        self.model = model
        self.weather = weather
        # 若未指定电价，使用模型中的分时电价（默认第一个费率）
        self.electricity_price = electricity_price
        # 将热容从 kJ/K 转换为 kWh/K
        self.thermal_capacity_kwh_k = model.thermal_capacity_kj_k / 3600.0
        # 状态变量
        self.indoor_temp_c: float = model.design_indoor_temp_c
        self.battery_soc_kwh: float = (
            model.battery.capacity_kwh if model.battery else 0.0
        )

    def _get_electricity_price(self, hour: int) -> float:
        """获取指定小时的电价。"""
        if self.electricity_price is not None:
            return self.electricity_price
        return self.model.electricity_price_at(hour)

    def run(self, strategy: Strategy, hours: int = 48) -> SimulationResult:
        """运行仿真并返回结果。"""
        result = SimulationResult(snapshots=[])

        for h in range(hours):
            decision = strategy.get(h)
            weather_pt = self.weather.get(h)

            snapshot = self._step(h, weather_pt, decision)
            result.snapshots.append(snapshot)

            # 累积总计
            result.total_energy_kwh += snapshot.total_power_kw
            result.total_carbon_kg += snapshot.carbon_kg
            result.total_water_l += snapshot.water_consumption_l
            result.total_cost_cny += snapshot.cost_cny
            if snapshot.indoor_temp_c > self.MAX_INDOOR_TEMP_C:
                result.temp_violations += 1
            if self.model.battery and self.battery_soc_kwh < (
                self.model.battery.min_soc * self.model.battery.capacity_kwh
            ):
                result.soc_violations += 1

        if result.snapshots:
            result.avg_pue = sum(s.pue for s in result.snapshots) / len(result.snapshots)
            result.max_indoor_temp_c = max(s.indoor_temp_c for s in result.snapshots)

        return result

    def _step(self, hour: int, weather: "WeatherPoint", decision: StrategyDecision) -> HourlySnapshot:
        """执行单小时仿真步进。"""
        m = self.model

        # === 1. IT 负载 ===
        it_util = max(0.0, min(1.0, decision.it_utilization))
        it_power_kw = 0.0
        for dev in m.devices:
            it_power_kw += dev.power_at_util(it_util) / 1000.0
        it_heat_kw = it_power_kw  # 简化：全部电能转化为热

        # === 2. 光伏出力 ===
        solar_kw = 0.0
        if m.solar:
            solar_kw = m.solar.output_kw(weather.solar_irradiance_w_m2)

        # === 3. 冷负荷计算（RC 模型） ===
        # 传热负荷
        envelope_load_kw = (
            m.envelope_u * m.envelope_area_m2 * (weather.temp_c - self.indoor_temp_c) / 1000.0
        )
        total_cooling_load_kw = it_heat_kw + envelope_load_kw

        # === 4. 冷却系统响应 ===
        # 免费冷却基于湿球温度判断，且需要冷冻水设定点足够高才能利用
        # （蒸发温度越高，越能利用室外免费冷源）
        free_cooling_temp_available = (
            weather.wet_bulb_temp_c <= m.coolers[0].free_cooling_threshold_c if m.coolers else False
        )
        free_cooling_setpoint_enabled = decision.chiller_setpoint_c >= 16.0
        free_cooling_possible = free_cooling_temp_available and free_cooling_setpoint_enabled

        # 分配冷负荷到各冷却单元
        actual_cooling_kw, cooling_power_kw, cop, fc_active, water_l = self._run_cooling(
            total_cooling_load_kw, free_cooling_possible, decision.chiller_setpoint_c
        )

        # === 5. 泵/风机功耗 ===
        pump_power_kw = self._run_pumps(total_cooling_load_kw)

        # === 6. 电池调度 ===
        battery_charge_kw = self._run_battery(
            solar_kw, it_power_kw, cooling_power_kw + pump_power_kw, decision
        )

        # === 7. 机械系统基础功耗 ===
        mechanical_base_kw = it_power_kw * m.pue_mechanical_baseline

        # === 8. 市电需求（变压器输入前） ===
        net_demand_before_loss_kw = (
            it_power_kw + cooling_power_kw + pump_power_kw + mechanical_base_kw
        )

        # === 9. 变压器损耗 ===
        transformer_loss_kw, transformer_eff = self._run_transformers(net_demand_before_loss_kw - solar_kw)

        # === 10. 配电损耗（旧模型回退 + 变压器模型叠加） ===
        electrical_loss_kw = net_demand_before_loss_kw * m.pue_electrical_loss

        total_demand_kw = net_demand_before_loss_kw + electrical_loss_kw + transformer_loss_kw

        grid_power_kw = total_demand_kw - solar_kw + battery_charge_kw
        # battery_charge_kw > 0 表示充电（增加电网需求），< 0 表示放电（减少电网需求）
        grid_power_kw = max(0.0, grid_power_kw)  # 不回馈电网

        # === 11. 更新室内温度 ===
        # dT = (Q_cooling 不足部分) / thermal_capacity
        cooling_shortfall_kw = max(0.0, total_cooling_load_kw - actual_cooling_kw)
        if self.thermal_capacity_kwh_k > 0:
            dt = cooling_shortfall_kw * self.TIME_STEP_H / self.thermal_capacity_kwh_k
            self.indoor_temp_c += dt
        # 温度不应不合理地低于室外温度过多（自然传热通过 envelope 已处理）
        self.indoor_temp_c = max(weather.temp_c - 10.0, self.indoor_temp_c)

        # === 12. 计算指标 ===
        total_power_kw = grid_power_kw + solar_kw - max(0, battery_charge_kw)
        pue = total_power_kw / it_power_kw if it_power_kw > 0 else 1.0

        carbon_intensity = m.carbon_intensity_at(hour)
        carbon_kg = grid_power_kw * carbon_intensity

        cost_cny = grid_power_kw * self._get_electricity_price(hour)

        return HourlySnapshot(
            hour=hour,
            outdoor_temp_c=weather.temp_c,
            solar_irradiance_w_m2=weather.solar_irradiance_w_m2,
            it_utilization=it_util,
            chiller_setpoint_c=decision.chiller_setpoint_c,
            it_power_kw=round(it_power_kw, 2),
            it_heat_kw=round(it_heat_kw, 2),
            solar_output_kw=round(solar_kw, 2),
            battery_soc_kwh=round(self.battery_soc_kwh, 2),
            battery_charge_kw=round(battery_charge_kw, 2),
            grid_power_kw=round(grid_power_kw, 2),
            indoor_temp_c=round(self.indoor_temp_c, 1),
            cooling_load_kw=round(total_cooling_load_kw, 2),
            cooling_power_kw=round(cooling_power_kw, 2),
            pump_power_kw=round(pump_power_kw, 2),
            mechanical_power_kw=round(mechanical_base_kw, 2),
            transformer_loss_kw=round(transformer_loss_kw, 2),
            free_cooling_active=fc_active,
            cop_actual=round(cop, 2),
            transformer_efficiency=round(transformer_eff, 4),
            total_power_kw=round(total_power_kw, 2),
            pue=round(pue, 3),
            carbon_kg=round(carbon_kg, 3),
            water_consumption_l=round(water_l, 1),
            cost_cny=round(cost_cny, 2),
        )

    def _run_cooling(self, cooling_load_kw: float, free_cooling_possible: bool,
                     chiller_setpoint_c: float) -> tuple[float, float, float, bool, float]:
        """运行冷却系统，返回 (实际制冷量, 冷却功耗, COP, 是否免费冷却, 水消耗L)。"""
        m = self.model
        if not m.coolers or cooling_load_kw <= 0:
            # 无冷负荷或自然散热
            if cooling_load_kw < 0:
                # 室外冷，室内散热 → 温度会自然下降
                self.indoor_temp_c -= abs(cooling_load_kw) * self.TIME_STEP_H / self.thermal_capacity_kwh_k
            return max(0.0, cooling_load_kw), 0.0, 0.0, False, 0.0

        # 免费冷却
        if free_cooling_possible:
            # 免费冷却直接利用室外冷空气，不消耗压缩机电能
            # 假设免费冷却可达制冷量的 80%
            fc_capacity = m.total_cooling_capacity_kw * 0.8
            cooling_delivered = min(cooling_load_kw, fc_capacity)
            # 免费冷却仍有风扇功耗（约额定制冷量的 5%）
            fan_power = cooling_delivered * 0.05
            # 如果免费冷却不够，剩余由机械制冷补充
            remaining_load = cooling_load_kw - cooling_delivered
            if remaining_load > 0:
                mech_cooling, mech_power, mech_cop = self._mechanical_cooling(remaining_load, chiller_setpoint_c)
                total_power = fan_power + mech_power
                total_cooling = cooling_delivered + mech_cooling
                return total_cooling, total_power, mech_cop, True, 0.0
            # 水消耗：免费冷却模式无水消耗
            return cooling_delivered, fan_power, 20.0, True, 0.0

        # 全机械制冷
        mech_cooling, mech_power, mech_cop = self._mechanical_cooling(cooling_load_kw, chiller_setpoint_c)
        water_l = mech_power * m.coolers[0].water_consumption_l_per_kwh
        return mech_cooling, mech_power, mech_cop, False, water_l

    def _mechanical_cooling(self, load_kw: float, chiller_setpoint_c: float) -> tuple[float, float, float]:
        """机械制冷：台数控制 + 负载分配 + 设定点修正，返回 (制冷量, 功耗, 加权COP)。"""
        m = self.model
        if not m.coolers or load_kw <= 0:
            return 0.0, 0.0, 0.0

        # 设定点修正：设定点越高，蒸发温度越高，COP 越高（每高 1°C 提升 5%）
        setpoint_delta = chiller_setpoint_c - self.COP_REFERENCE_SETPOINT_C
        setpoint_factor = max(0.7, 1.0 + setpoint_delta * self.COP_SETPOINT_PENALTY_PER_C)

        # 台数控制：确定最少需要开几台来满足负荷（每台至少 min_part_load）
        coolers_sorted = sorted(m.coolers, key=lambda c: c.capacity_kw)
        total_power = 0.0
        total_cooling = 0.0
        remaining_load = load_kw

        for cooler in coolers_sorted:
            if remaining_load <= 0:
                break
            # 本台可承担的最大负荷
            max_per = cooler.capacity_kw
            min_per = cooler.capacity_kw * cooler.min_part_load_ratio
            # 如果剩余负荷 < 最小部分负载，但仍需制冷 → 运行在最小负载
            if remaining_load < min_per:
                actual = min_per
            else:
                actual = min(remaining_load, max_per)
            lr = actual / cooler.capacity_kw
            cop = cooler.cop_at_load(lr) * setpoint_factor
            power = actual / cop if cop > 0 else 0
            total_cooling += actual
            total_power += power
            remaining_load -= actual

        # 如果所有冷却器都满载还不够
        capped_cooling = min(load_kw, m.total_cooling_capacity_kw)
        avg_cop = capped_cooling / total_power if total_power > 0 else 3.0

        return capped_cooling, total_power, avg_cop

    def _run_pumps(self, cooling_load_kw: float) -> float:
        """计算冷却系统泵/风机功耗。"""
        m = self.model
        if cooling_load_kw <= 0:
            return 0.0
        if m.cooling_architecture in ("liquid-cooled", "hybrid"):
            # 液冷：泵功耗与冷却负荷成正比
            return cooling_load_kw * self.LIQUID_PUMP_W_PER_KW_LOAD
        # 风冷：风机额外功耗（已部分隐含在冷却器 COP 中，此处只加小量）
        return cooling_load_kw * self.LIQUID_PUMP_HEAD_FACTOR

    def _run_transformers(self, demand_kw: float) -> tuple[float, float]:
        """计算变压器损耗和综合效率。

        返回 (损耗 kW, 综合效率)。
        """
        m = self.model
        if not m.transformers:
            # 旧模型回退：固定配电损耗已在 _step 中计算
            return 0.0, 1.0 - m.pue_electrical_loss

        total_capacity_kw = sum(tr.capacity_mva * 1000 for tr in m.transformers)
        if total_capacity_kw <= 0:
            return 0.0, 0.99

        # 假设负载均匀分配到各变压器
        load_ratio = demand_kw / total_capacity_kw
        avg_efficiency = 0.0
        for tr in m.transformers:
            avg_efficiency += tr.efficiency_at_load(load_ratio)
        avg_efficiency /= len(m.transformers)
        avg_efficiency = max(0.5, min(1.0, avg_efficiency))

        # 损耗 = 输出功率 × (1/效率 - 1)
        output_kw = max(0.0, demand_kw)
        if avg_efficiency >= 1.0:
            return 0.0, avg_efficiency
        loss_kw = output_kw * (1.0 / avg_efficiency - 1.0)
        return loss_kw, avg_efficiency

    def _run_battery(self, solar_kw: float, it_power_kw: float,
                     cooling_power_kw: float, decision: StrategyDecision) -> float:
        """运行储能调度，返回电池充放电功率 (+充电, -放电)。"""
        battery = self.model.battery
        if not battery:
            return 0.0

        mode = decision.battery_mode
        battery_kw = 0.0

        if mode == "charge":
            # 用光伏余电充电
            surplus = solar_kw - (it_power_kw + cooling_power_kw)
            charge_kw = min(
                max(0.0, surplus),
                battery.max_charge_kw,
                (battery.capacity_kwh - self.battery_soc_kwh) / self.TIME_STEP_H,
            )
            self.battery_soc_kwh += charge_kw * battery.roundtrip_efficiency
            battery_kw = charge_kw

        elif mode == "discharge":
            # 放电削减市电
            deficit = (it_power_kw + cooling_power_kw) - solar_kw
            discharge_kw = min(
                max(0.0, deficit),
                battery.max_discharge_kw,
                (self.battery_soc_kwh - battery.min_soc * battery.capacity_kwh) / self.TIME_STEP_H,
            )
            self.battery_soc_kwh -= discharge_kw
            battery_kw = -discharge_kw

        elif mode == "auto":
            # 自动模式：光伏余电充电，电网缺电时放电
            surplus = solar_kw - (it_power_kw + cooling_power_kw)
            if surplus > 0:
                # 充电
                charge_kw = min(surplus, battery.max_charge_kw,
                                (battery.capacity_kwh - self.battery_soc_kwh) / self.TIME_STEP_H)
                self.battery_soc_kwh += charge_kw * battery.roundtrip_efficiency
                battery_kw = charge_kw
            else:
                # 放电（仅在 SOC > 50% 时进行，保留应急储备）
                if self.battery_soc_kwh > battery.capacity_kwh * 0.5:
                    discharge_kw = min(-surplus, battery.max_discharge_kw,
                                       (self.battery_soc_kwh - battery.min_soc * battery.capacity_kwh) / self.TIME_STEP_H)
                    self.battery_soc_kwh -= discharge_kw
                    battery_kw = -discharge_kw

        # 待机损耗
        self.battery_soc_kwh -= battery.standby_loss_kw * self.TIME_STEP_H

        # SOC 边界
        self.battery_soc_kwh = max(battery.min_soc * battery.capacity_kwh,
                                   min(battery.capacity_kwh, self.battery_soc_kwh))

        return battery_kw
