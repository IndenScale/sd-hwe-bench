"""物理模型定义——从 ADL YAML 加载的房间热物理参数、天气曲线、设备特性。"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class WeatherPoint:
    """单个时间点的天气数据。"""

    hour: int                    # 0-23
    temp_c: float                # 室外干球温度 ℃
    humidity_pct: float          # 相对湿度 %
    wet_bulb_temp_c: float       # 湿球温度 ℃
    solar_irradiance_w_m2: float # 太阳辐照度 W/m² (0 表示夜间)
    wind_speed_m_s: float       # 风速 m/s


@dataclass
class AIDCWeatherProfile:
    """48 小时天气曲线（从 CSV 或合成数据加载）。"""

    points: list[WeatherPoint] = field(default_factory=list)

    @classmethod
    def from_csv(cls, path: Path) -> "AIDCWeatherProfile":
        """从 CSV 加载（hour,temp_c,humidity_pct,solar_wm2,wind_ms）。"""
        import csv
        points = []
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                temp_c = float(row["temp_c"])
                humidity_pct = float(row["humidity_pct"])
                points.append(WeatherPoint(
                    hour=int(row["hour"]),
                    temp_c=temp_c,
                    humidity_pct=humidity_pct,
                    wet_bulb_temp_c=float(row.get("wet_bulb_c", cls._wet_bulb_temp(temp_c, humidity_pct))),
                    solar_irradiance_w_m2=float(row.get("solar_wm2", 0)),
                    wind_speed_m_s=float(row.get("wind_ms", 0)),
                ))
        return cls(points=points)

    @staticmethod
    def _wet_bulb_temp(temp_c: float, humidity_pct: float) -> float:
        """使用 Stull (2011) 简化公式估算湿球温度。"""
        rh = max(0.0, min(100.0, humidity_pct))
        t = temp_c
        wb = (
            t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )
        return wb

    @classmethod
    def synthetic_summer_day(cls, peak_temp_c: float = 35.0, night_temp_c: float = 25.0) -> "AIDCWeatherProfile":
        """生成合成夏季 48 小时天气曲线（正弦波近似，无太阳能数据时使用默认夏季辐照）。"""
        points = []
        # 夏季典型辐照曲线峰值 ~800 W/m² 在 12:00
        for h in range(48):
            hour_of_day = h % 24
            # 温度：正弦波，14:00 峰值，4:00 谷底
            temp = night_temp_c + (peak_temp_c - night_temp_c) * (
                0.5 + 0.5 * math.sin((hour_of_day - 8) * math.pi / 12)
            )
            # 湿度：与温度反相关；夜间绝对湿度相近，相对湿度更高
            humidity = max(45.0, 90.0 - (temp - night_temp_c) * 4.0)
            wet_bulb = cls._wet_bulb_temp(temp, humidity)
            # 太阳辐照：6:00-18:00 正弦
            if 6 <= hour_of_day <= 18:
                solar = 800.0 * math.sin((hour_of_day - 6) * math.pi / 12)
            else:
                solar = 0.0
            points.append(WeatherPoint(
                hour=h, temp_c=round(temp, 1),
                humidity_pct=round(humidity, 1),
                wet_bulb_temp_c=round(wet_bulb, 1),
                solar_irradiance_w_m2=round(solar, 1),
                wind_speed_m_s=2.0,
            ))
        return cls(points=points)

    @classmethod
    def synthetic_winter_day(cls, peak_temp_c: float = 10.0, night_temp_c: float = -2.0) -> "AIDCWeatherProfile":
        """生成合成冬季 48 小时天气曲线。"""
        points = []
        for h in range(48):
            hour_of_day = h % 24
            temp = night_temp_c + (peak_temp_c - night_temp_c) * (
                0.5 + 0.5 * math.sin((hour_of_day - 8) * math.pi / 12)
            )
            humidity = max(40.0, min(90.0, 70.0 - (temp - night_temp_c) * 2.0))
            wet_bulb = cls._wet_bulb_temp(temp, humidity)
            if 7 <= hour_of_day <= 17:
                solar = 400.0 * math.sin((hour_of_day - 7) * math.pi / 10)
            else:
                solar = 0.0
            points.append(WeatherPoint(
                hour=h, temp_c=round(temp, 1),
                humidity_pct=round(humidity, 1),
                wet_bulb_temp_c=round(wet_bulb, 1),
                solar_irradiance_w_m2=round(solar, 1),
                wind_speed_m_s=2.0,
            ))
        return cls(points=points)

    def get(self, hour: int) -> WeatherPoint:
        """获取指定小时的天气数据（支持超出 48h 的循环）。"""
        return self.points[hour % len(self.points)]


@dataclass
class CoolerSpec:
    """单台冷却设备的规格参数。"""

    id: str
    capacity_kw: float
    cop_nominal: float
    cop_curve: list[tuple[float, float]]  # [(load_ratio, cop), ...]
    free_cooling_threshold_c: float
    water_consumption_l_per_kwh: float
    min_part_load_ratio: float = 0.2

    def cop_at_load(self, load_ratio: float) -> float:
        """根据负载率插值 COP。"""
        if load_ratio <= 0:
            return 0.0
        load_ratio = max(self.min_part_load_ratio, min(1.0, load_ratio))
        curve = sorted(self.cop_curve)
        # 线性插值
        for i, (lr, cop) in enumerate(curve):
            if lr >= load_ratio:
                if i == 0:
                    return cop
                prev_lr, prev_cop = curve[i - 1]
                frac = (load_ratio - prev_lr) / (lr - prev_lr)
                return prev_cop + frac * (cop - prev_cop)
        return curve[-1][1]


@dataclass
class BatterySpec:
    """储能设备规格。"""

    id: str
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    roundtrip_efficiency: float
    standby_loss_kw: float = 0.05
    min_soc: float = 0.10         # 最低 SOC
    current_soc_kwh: float = 50.0 # 初始 SOC


@dataclass
class SolarSpec:
    """光伏阵列规格。"""

    id: str
    peak_power_kw: float
    inverter_efficiency: float

    def output_kw(self, irradiance_w_m2: float) -> float:
        """根据太阳辐照度计算光伏输出功率。"""
        # 标况辐照度 1000 W/m²
        ratio = irradiance_w_m2 / 1000.0
        dc_power = self.peak_power_kw * ratio
        return dc_power * self.inverter_efficiency


@dataclass
class DeviceSpec:
    """单个 IT 设备的功耗特性。"""

    id: str
    model_name: str
    tdp_w: float
    idle_power_w: float
    util_to_power_ratio: float   # 功耗随利用率的线性系数
    psu_efficiency: float = 0.94

    def power_at_util(self, cpu_util: float) -> float:
        """根据 CPU 利用率计算实际功耗。"""
        dynamic = (self.tdp_w - self.idle_power_w) * cpu_util * self.util_to_power_ratio
        dc_power = self.idle_power_w + dynamic
        return dc_power / self.psu_efficiency  # AC 功耗


@dataclass
class TransformerSpec:
    """变压器规格与效率曲线。"""

    id: str
    capacity_mva: float
    efficiency_curve: list[tuple[float, float]] = field(default_factory=list)

    def efficiency_at_load(self, load_ratio: float) -> float:
        """根据负载率插值效率（输出/输入）。"""
        if not self.efficiency_curve:
            return 0.99
        load_ratio = max(0.0, min(1.0, load_ratio))
        curve = sorted(self.efficiency_curve)
        for i, (lr, eff) in enumerate(curve):
            if lr >= load_ratio:
                if i == 0:
                    return eff
                prev_lr, prev_eff = curve[i - 1]
                frac = (load_ratio - prev_lr) / (lr - prev_lr)
                return prev_eff + frac * (eff - prev_eff)
        return curve[-1][1]


@dataclass
class TimeOfUseRate:
    """分时费率段。"""

    hours: str          # "0-7,23" 或 "8-17"
    price: float        # 元/kWh 或 kgCO₂/kWh

    def matches(self, hour: int) -> bool:
        """判断某小时是否落在本费率段。"""
        for part in self.hours.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo.strip()) <= hour <= int(hi.strip()):
                    return True
            else:
                if int(part) == hour:
                    return True
        return False


@dataclass
class LifecycleCostConfig:
    """全生命周期成本参数。"""

    project_lifetime_years: int = 15
    discount_rate: float = 0.08
    water_price_cny_per_m3: float = 5.0
    # CAPEX 单位成本
    chiller_cny_per_kw: float = 1200.0
    cdu_cny_per_kw: float = 2500.0
    cooling_tower_cny_per_kw: float = 300.0
    transformer_cny_per_mva: float = 800000.0
    ups_cny_per_kw: float = 400.0
    battery_cny_per_kwh: float = 1200.0
    solar_cny_per_kwp: float = 3500.0
    rack_cny_per_unit: float = 80000.0
    civil_cny_per_m2: float = 12000.0
    # OPEX 年费率（占 CAPEX 比例）
    cooling_opex_rate: float = 0.04
    electrical_opex_rate: float = 0.025
    battery_opex_rate: float = 0.03
    solar_opex_rate: float = 0.015
    # 收益
    it_revenue_cny_per_kw_year: float = 8000.0
    gpu_depreciation_years: float = 4.0

    @classmethod
    def from_dict(cls, data: dict) -> "LifecycleCostConfig":
        """从 room YAML 的 lifecycle 段解析。"""
        cfg = cls()
        if not isinstance(data, dict):
            return cfg
        cfg.project_lifetime_years = int(data.get("project_lifetime_years", 15))
        cfg.discount_rate = float(data.get("discount_rate", 0.08))
        cfg.water_price_cny_per_m3 = float(data.get("water_price_cny_per_m3", 5.0))
        capex = data.get("capex", {})
        cfg.chiller_cny_per_kw = float(capex.get("chiller_10mw_cny_per_kw", 1200.0))
        cfg.cdu_cny_per_kw = float(capex.get("cdu_2mw_cny_per_kw", 2500.0))
        cfg.cooling_tower_cny_per_kw = float(capex.get("cooling_tower_cny_per_kw", 300.0))
        cfg.transformer_cny_per_mva = float(capex.get("transformer_40mva_cny_per_mva", 800000.0))
        cfg.ups_cny_per_kw = float(capex.get("ups_cny_per_kw", 400.0))
        cfg.battery_cny_per_kwh = float(capex.get("battery_cny_per_kwh", 1200.0))
        cfg.solar_cny_per_kwp = float(capex.get("solar_cny_per_kwp", 3500.0))
        cfg.rack_cny_per_unit = float(capex.get("rack_cny_per_unit", 80000.0))
        cfg.civil_cny_per_m2 = float(capex.get("civil_cny_per_m2", 12000.0))
        opex = data.get("opex_rate", {})
        cfg.cooling_opex_rate = float(opex.get("cooling", 0.04))
        cfg.electrical_opex_rate = float(opex.get("electrical", 0.025))
        cfg.battery_opex_rate = float(opex.get("battery", 0.03))
        cfg.solar_opex_rate = float(opex.get("solar", 0.015))
        revenue = data.get("revenue", {})
        cfg.it_revenue_cny_per_kw_year = float(revenue.get("it_revenue_cny_per_kw_year", 8000.0))
        cfg.gpu_depreciation_years = float(revenue.get("gpu_depreciation_years", 4.0))
        return cfg


@dataclass
class AIDCRoomModel:
    """从 ADL room YAML 加载的完整房间物理模型。"""

    room_id: str
    name: str = ""
    # 几何
    length_m: float = 12.0
    width_m: float = 8.0
    height_m: float = 3.2
    floor_area_m2: float = 96.0
    room_volume_m3: float = 307.2
    # 热物理
    envelope_u: float = 0.5            # W/(m²·K)
    envelope_area_m2: float = 256.0
    thermal_capacity_kj_k: float = 15000.0
    design_indoor_temp_c: float = 24.0
    supply_air_temp_c: float = 18.0
    hot_aisle_temp_limit_c: float = 45.0
    # 空调系统总容量（所有冷却单元加总）
    total_cooling_capacity_kw: float = 120.0
    cooling_architecture: str = "air-cooled"  # air-cooled | liquid-cooled | hybrid
    # 设备
    devices: list[DeviceSpec] = field(default_factory=list)
    coolers: list[CoolerSpec] = field(default_factory=list)
    battery: Optional[BatterySpec] = None
    solar: Optional[SolarSpec] = None
    # 配电
    grid_capacity_kw: float = 200.0
    grid_carbon_intensity: float = 0.581  # kgCO₂/kWh，默认值
    pue_mechanical_baseline: float = 0.15  # 除冷却外的机械系统占比
    pue_electrical_loss: float = 0.03      # 配电损耗（旧模型回退）
    transformers: list[TransformerSpec] = field(default_factory=list)
    electricity_price_profile: list[TimeOfUseRate] = field(default_factory=list)
    grid_carbon_profile: list[TimeOfUseRate] = field(default_factory=list)
    # 全生命周期成本
    lifecycle: LifecycleCostConfig = field(default_factory=LifecycleCostConfig)
    # 总 IT 设备 TDP（从 devices 自动计算，也可覆盖）
    total_it_tdp_kw: float = 0.0

    def __post_init__(self):
        if self.total_it_tdp_kw == 0.0 and self.devices:
            self.total_it_tdp_kw = sum(d.tdp_w for d in self.devices) / 1000.0

    def electricity_price_at(self, hour: int) -> float:
        """获取指定小时的电价（元/kWh）。"""
        for rate in self.electricity_price_profile:
            if rate.matches(hour % 24):
                return rate.price
        return 0.75

    def carbon_intensity_at(self, hour: int) -> float:
        """获取指定小时的电网碳排放强度（kgCO₂/kWh）。"""
        for rate in self.grid_carbon_profile:
            if rate.matches(hour % 24):
                return rate.price
        return self.grid_carbon_intensity

    @classmethod
    def from_adl_project(cls, project_dir: Path, room_id: str = "DC-HALL-A") -> "AIDCRoomModel":
        """从 ADL 项目目录加载房间模型。

        读取 rooms/<room_id>.yaml → 解析热物理参数 → 加载关联的设备模型和实例。
        """
        room_file = project_dir / "rooms" / f"{room_id}.yaml"
        if not room_file.exists():
            raise FileNotFoundError(f"Room file not found: {room_file}")

        with open(room_file) as f:
            room_data = yaml.safe_load(f)

        model = cls(
            room_id=room_id,
            name=room_data.get("name", ""),
            length_m=room_data.get("length_mm", 12000) / 1000,
            width_m=room_data.get("width_mm", 8000) / 1000,
            height_m=room_data.get("height_mm", 3200) / 1000,
            floor_area_m2=room_data.get("floor_area_m2", 96.0),
            room_volume_m3=room_data.get("room_volume_m3", 307.2),
        )

        # 热物理参数
        thermal = room_data.get("thermal", {})
        if thermal:
            model.envelope_u = thermal.get("envelope_u_value_w_m2k", 0.5)
            model.envelope_area_m2 = thermal.get("envelope_area_m2", 256.0)
            model.thermal_capacity_kj_k = thermal.get("thermal_capacity_kj_k", 15000.0)
            model.design_indoor_temp_c = thermal.get("design_indoor_temp_c", 24.0)
            model.supply_air_temp_c = thermal.get("supply_air_temp_c", 18.0)
            model.hot_aisle_temp_limit_c = thermal.get("hot_aisle_temp_limit_c", 45.0)

        # 冷却设备
        cooling = room_data.get("cooling", {})
        if cooling:
            model.cooling_architecture = cooling.get("architecture", "air-cooled")
            coolers = cooling.get("units", [])
            for cu in coolers:
                cop_curve = cu.get("cop_curve", [[0.2, 3.0], [0.4, 3.8], [0.6, 4.5], [0.8, 4.8], [1.0, 5.0]])
                model.coolers.append(CoolerSpec(
                    id=cu.get("id", ""),
                    capacity_kw=float(cu.get("capacity_kw", 30.0)),
                    cop_nominal=float(cu.get("cop_nominal", 4.5)),
                    cop_curve=[(float(p[0]), float(p[1])) for p in cop_curve],
                    free_cooling_threshold_c=float(cu.get("free_cooling_threshold_c", 15.0)),
                    water_consumption_l_per_kwh=float(cu.get("water_consumption_l_per_kwh", 0.8)),
                ))
            model.total_cooling_capacity_kw = float(cooling.get("total_capacity_kw", 120.0))

        # 配电
        power_cfg = room_data.get("power", {})
        if power_cfg:
            model.grid_capacity_kw = float(power_cfg.get("grid_capacity_kw", 200.0))
            model.pue_mechanical_baseline = float(power_cfg.get("pue_mechanical_baseline", 0.15))
            model.pue_electrical_loss = float(power_cfg.get("pue_electrical_loss", 0.03))
            # 碳强度：优先使用分时配置，否则使用全局值
            grid_carbon_global = float(power_cfg.get("grid_carbon_intensity", 0.581))
            model.grid_carbon_intensity = grid_carbon_global
            model.grid_carbon_profile = cls._parse_tou_profile(
                power_cfg.get("grid_carbon_intensity_profile", []),
                default_price=grid_carbon_global,
            )
            model.electricity_price_profile = cls._parse_tou_profile(
                power_cfg.get("electricity_price_profile", []),
                default_price=0.75,
            )
            # 变压器
            for tr in power_cfg.get("transformers", []):
                eff_curve = tr.get("efficiency_curve", [[0.25, 0.99], [0.5, 0.995], [0.75, 0.997], [1.0, 0.996]])
                model.transformers.append(TransformerSpec(
                    id=tr.get("id", ""),
                    capacity_mva=float(tr.get("capacity_mva", 1.0)),
                    efficiency_curve=[(float(p[0]), float(p[1])) for p in eff_curve],
                ))
            # 光伏/储能（兼容旧字段命名）
            solar_cfg = power_cfg
            model.solar = SolarSpec(
                id="SOLAR-ROOF",
                peak_power_kw=float(solar_cfg.get("solar_capacity_kwp", 20.0)),
                inverter_efficiency=0.97,
            )
            model.battery = BatterySpec(
                id="BATT-01",
                capacity_kwh=float(solar_cfg.get("battery_capacity_kwh", 50.0)),
                max_charge_kw=float(solar_cfg.get("battery_max_charge_rate_kw", 25.0)),
                max_discharge_kw=float(solar_cfg.get("battery_max_discharge_rate_kw", 25.0)),
                roundtrip_efficiency=float(solar_cfg.get("battery_charge_efficiency", 0.92)),
            )

        # 全生命周期成本
        lifecycle_cfg = room_data.get("lifecycle", {})
        if lifecycle_cfg:
            model.lifecycle = LifecycleCostConfig.from_dict(lifecycle_cfg)

        # 加载设备列表（从 instances/devices/）
        model.devices = cls._load_devices(project_dir)
        if model.devices:
            model.total_it_tdp_kw = sum(d.tdp_w for d in model.devices) / 1000.0

        return model

    @staticmethod
    def _parse_tou_profile(entries: list[dict], default_price: float) -> list[TimeOfUseRate]:
        """解析分时费率配置。"""
        if not entries:
            return [TimeOfUseRate(hours="0-23", price=default_price)]
        rates = []
        for e in entries:
            rates.append(TimeOfUseRate(
                hours=str(e.get("hours", "0-23")),
                price=float(e.get("price", e.get("intensity", default_price))),
            ))
        return rates

    @staticmethod
    def _load_devices(project_dir: Path) -> list[DeviceSpec]:
        """从 ADL instances 加载 IT 设备列表。"""
        devices: list[DeviceSpec] = []
        devices_dir = project_dir / "instances" / "devices"
        if not devices_dir.exists():
            return devices

        for yf in sorted(devices_dir.glob("*.yaml")):
            with open(yf) as f:
                data = yaml.safe_load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                family = item.get("family", "")
                if family not in ("ServerFamily", "StorageFamily"):
                    continue
                model_name = item.get("model", "")
                device_id = item.get("id", "")
                # 尝试从模型文件加载详细参数
                tdp_w, idle_w, util_ratio, psu_eff = 500.0, 120.0, 0.7, 0.94
                model_file = project_dir / "models" / "devices" / f"{model_name}.yaml"
                if model_file.exists():
                    with open(model_file) as mf:
                        mdata = yaml.safe_load(mf)
                    tdp_w = float(mdata.get("tdp_w", 500))
                    idle_w = float(mdata.get("idle_power_w", 120))
                    util_ratio = float(mdata.get("cpu_util_to_power_ratio", 0.7))
                    psu_eff = float(mdata.get("psu_efficiency", 0.94))

                devices.append(DeviceSpec(
                    id=device_id,
                    model_name=model_name,
                    tdp_w=tdp_w,
                    idle_power_w=idle_w,
                    util_to_power_ratio=util_ratio,
                    psu_efficiency=psu_eff,
                ))
        return devices
