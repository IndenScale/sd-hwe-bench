"""运营策略 DSL — Agent 产出的策略描述格式。

策略文件格式（YAML/JSON）:

```yaml
strategy_name: "保守冷却策略"
description: "全天固定冷冻水温度 12°C，负载均匀"
decisions:
  - hour: [0, 23]    # 适用小时范围
    it_utilization: 0.7
    chiller_setpoint_c: 12.0
    battery_mode: auto
  - hour: [24, 47]
    it_utilization: 0.7
    chiller_setpoint_c: 12.0
    battery_mode: auto
```

或使用时段模板:

```yaml
strategy_name: "分时冷却策略"
description: "夜间免费冷却 + 峰值电价储能放电"
templates:
  - name: "daytime"
    hours: "9-17"
    it_utilization: 0.85
    chiller_setpoint_c: 10.0
    battery_mode: "auto"
  - name: "night"
    hours: "0-8,18-23"
    it_utilization: 0.4
    chiller_setpoint_c: 16.0
    battery_mode: "charge"
```
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from sd_hwe_bench.simulation.engine import Strategy, StrategyDecision


@dataclass
class StrategyTemplate:
    """时段模板。"""
    name: str
    hours: str = "0-23"           # "9-17" 或 "0-8,18-23"
    it_utilization: float = 0.7
    chiller_setpoint_c: float = 12.0
    battery_mode: str = "auto"
    load_shedding: bool = False

    def matches(self, hour: int) -> bool:
        """检查小时是否匹配模板（hours 按 24h 制，跨天循环）。"""
        hour_of_day = hour % 24
        for part in self.hours.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo.strip()) <= hour_of_day <= int(hi.strip()):
                    return True
            else:
                if int(part) == hour_of_day:
                    return True
        return False


@dataclass
class HourRangeDecision:
    """显式小时范围的决策。"""
    hour: list[int] = field(default_factory=lambda: [0, 23])
    it_utilization: float = 0.7
    chiller_setpoint_c: float = 12.0
    battery_mode: str = "auto"
    load_shedding: bool = False


def parse_strategy_file(path: Path, hours: int = 48) -> Strategy:
    """从 YAML/JSON 策略文件解析为 Strategy 对象。"""
    with open(path) as f:
        data = yaml.safe_load(f)

    decisions = _expand_to_hourly(data, hours)
    return Strategy(decisions=decisions)


def parse_strategy_dict(data: dict, hours: int = 48) -> Strategy:
    """从 dict 解析策略。"""
    decisions = _expand_to_hourly(data, hours)
    return Strategy(decisions=decisions)


def _expand_to_hourly(data: dict, hours: int) -> list[StrategyDecision]:
    """将策略描述展开为逐小时决策列表。"""
    decisions: list[Optional[StrategyDecision]] = [None] * hours

    # 方式 1：templates（时段模板）
    templates = data.get("templates", [])
    for t_data in templates:
        tmpl = StrategyTemplate(
            name=t_data.get("name", ""),
            hours=t_data.get("hours", "0-23"),
            it_utilization=float(t_data.get("it_utilization", 0.7)),
            chiller_setpoint_c=float(t_data.get("chiller_setpoint_c", 12.0)),
            battery_mode=t_data.get("battery_mode", "auto"),
            load_shedding=t_data.get("load_shedding", False),
        )
        for h in range(hours):
            if tmpl.matches(h):
                decisions[h] = StrategyDecision(
                    it_utilization=tmpl.it_utilization,
                    chiller_setpoint_c=tmpl.chiller_setpoint_c,
                    battery_mode=tmpl.battery_mode,
                    load_shedding=tmpl.load_shedding,
                )

    # 方式 2：decisions（显式小时范围）
    range_decisions = data.get("decisions", [])
    for rd in range_decisions:
        hour_range = rd.get("hour", [0, 23])
        lo, hi = hour_range[0], hour_range[-1]
        dec = StrategyDecision(
            it_utilization=float(rd.get("it_utilization", 0.7)),
            chiller_setpoint_c=float(rd.get("chiller_setpoint_c", 12.0)),
            battery_mode=rd.get("battery_mode", "auto"),
            load_shedding=rd.get("load_shedding", False),
        )
        for h in range(lo, hi + 1):
            if h < hours:
                decisions[h] = dec

    # 填充未指定的小时（使用默认值）
    for h in range(hours):
        if decisions[h] is None:
            decisions[h] = StrategyDecision()

    return decisions


def make_baseline_strategy(hours: int = 48) -> Strategy:
    """生成基线策略：固定设定点，无优化。"""
    return Strategy(decisions=[
        StrategyDecision(
            it_utilization=0.7,
            chiller_setpoint_c=12.0,
            battery_mode="idle",
        )
        for _ in range(hours)
    ])


def make_naive_fc_strategy(hours: int = 48) -> Strategy:
    """生成朴素免费冷却策略：全天固定 IT 负载，夜间提高设定点利用免费冷却。"""
    decisions = []
    for h in range(hours):
        hour_of_day = h % 24
        if 8 <= hour_of_day <= 20:
            decisions.append(StrategyDecision(
                it_utilization=0.7,
                chiller_setpoint_c=12.0,
                battery_mode="auto",
            ))
        else:
            decisions.append(StrategyDecision(
                it_utilization=0.7,
                chiller_setpoint_c=22.0,
                battery_mode="charge",
            ))
    return Strategy(decisions=decisions)


def make_aggressive_strategy(hours: int = 48) -> Strategy:
    """激进策略：最大限度利用免费冷却和储能。"""
    decisions = []
    for h in range(hours):
        hour_of_day = h % 24
        if 6 <= hour_of_day <= 18:
            decisions.append(StrategyDecision(
                it_utilization=0.8,
                chiller_setpoint_c=10.0,
                battery_mode="discharge",
            ))
        else:
            decisions.append(StrategyDecision(
                it_utilization=0.5,
                chiller_setpoint_c=18.0,
                battery_mode="charge",
            ))
    return Strategy(decisions=decisions)
