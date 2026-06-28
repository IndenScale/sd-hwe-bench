"""L4 AIDC 仿真合规 critic — 基于降阶物理模型的动态约束检查。

职责划分：
- 硬约束（PUE、温度、SOC 等）决定 passed，作为 L4 合规结果。
- 归一化优化分数作为诊断性 performance_score，不决定 passed。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.simulation.engine import AIDCSimulator, SimulationResult
from sd_hwe_bench.simulation.model import AIDCRoomModel, AIDCWeatherProfile
from sd_hwe_bench.simulation.strategy import (
    Strategy,
    make_baseline_strategy,
    parse_strategy_file,
    parse_strategy_dict,
)


class PerformanceCritic(Critic):
    """L4 AIDC 仿真合规检查与性能诊断。"""

    name = "L4-Simulation"

    # 权重分配 [PUE, 碳, 水, 成本]
    DEFAULT_OBJECTIVE_WEIGHTS = [0.3, 0.3, 0.15, 0.25]

    def __init__(
        self,
        project_dir: Path | None = None,
        weather: AIDCWeatherProfile | None = None,
        simulation_hours: int = 48,
        objective_weights: list[float] | None = None,
        objective: str = "performance",  # performance | lcc | combined
        canonical_project: Path | None = None,
        reference: dict | None = None,
        constraints: dict | None = None,
    ):
        self.project_dir = project_dir
        self.weather = weather
        self.simulation_hours = simulation_hours
        self.objective_weights = objective_weights or self.DEFAULT_OBJECTIVE_WEIGHTS
        self.objective = objective
        self.canonical_project = canonical_project
        self.reference = reference or {}
        self.constraints = constraints or {}

    def evaluate(self, workspace_root: Path, task: Any) -> CriticResult:
        """运行仿真并输出 L4 合规结果与性能诊断分数。"""
        # 1. 解析 task simulation config (legacy l7_config or new l4_config)
        sim_config = getattr(task.metadata, "l7_config", {}) if hasattr(task, "metadata") else {}
        if not sim_config and hasattr(task, "metadata"):
            sim_config = getattr(task.metadata, "l4_config", {}) or {}
        self._apply_l7_config(sim_config)

        # 2. 查找策略文件
        strategy = self._find_strategy(workspace_root, task)

        # 3. 加载房间模型（co-design 时优先从 workspace，否则从 canonical）
        model = self._load_model(task, workspace_root)

        # 4. 确定天气
        weather = self.weather or AIDCWeatherProfile.synthetic_summer_day()

        # 5. 运行 Agent 仿真
        sim = AIDCSimulator(model, weather)
        result = sim.run(strategy, hours=self.simulation_hours)

        # 6. 运行基线仿真
        baseline_result = self._run_baseline(model, weather)

        # 7. 计算 LCC（如需要）
        lcc_agent = None
        lcc_baseline = None
        if self.objective in ("lcc", "combined"):
            from sd_hwe_bench.simulation.lifecycle import evaluate_lcc
            lcc_agent = evaluate_lcc(model, result)
            # 基线 LCC 使用同一模型（co-design 时 baseline_model 可能不同，已在 _run_baseline 中确定）
            baseline_model = getattr(self, "_last_baseline_model", model)
            lcc_baseline = evaluate_lcc(baseline_model, baseline_result)

        # 8. 计算归一化得分（诊断）与硬约束合规
        perf_score, details = self._compute_score(result, baseline_result, lcc_agent, lcc_baseline)
        compliance = self._check_compliance(result, lcc_agent)
        details["compliance"] = compliance

        artifacts = {
            "simulation_result": result.summary(),
            "baseline_result": baseline_result.summary(),
            "score_breakdown": details,
        }
        if lcc_agent:
            artifacts["lcc_result"] = lcc_agent.summary()
        if lcc_baseline:
            artifacts["lcc_baseline"] = lcc_baseline.summary()

        comments = [json.dumps(details, ensure_ascii=False, indent=2)]
        if not compliance["passed"]:
            comments = compliance["violations"] + comments

        return CriticResult(
            name=self.name,
            passed=compliance["passed"],
            score=perf_score,
            comments=comments,
            artifacts=artifacts,
        )

    def _apply_l7_config(self, l7_config: dict) -> None:
        """根据 task simulation config 更新 critic 参数。"""
        if not l7_config:
            return
        weather_type = l7_config.get("weather", "summer")
        if self.weather is None:
            params = l7_config.get("weather_params", {})
            if weather_type == "summer":
                self.weather = AIDCWeatherProfile.synthetic_summer_day(
                    peak_temp_c=params.get("peak_temp_c", 35.0),
                    night_temp_c=params.get("night_temp_c", 25.0),
                )
            elif weather_type == "winter":
                self.weather = AIDCWeatherProfile.synthetic_winter_day(
                    peak_temp_c=params.get("peak_temp_c", 10.0),
                    night_temp_c=params.get("night_temp_c", -2.0),
                )
            else:
                self.weather = AIDCWeatherProfile.synthetic_summer_day()
        self.simulation_hours = l7_config.get("hours", self.simulation_hours)
        self.objective_weights = l7_config.get("objective_weights", self.objective_weights)
        self.objective = l7_config.get("objective", self.objective)
        self.reference = l7_config.get("reference", self.reference) or {}
        self.constraints = l7_config.get("constraints", self.constraints) or {}
        canonical = l7_config.get("canonical_project")
        if canonical and self.canonical_project is None:
            import sd_hwe_bench
            repo_root = Path(sd_hwe_bench.__file__).parent.parent.parent
            self.canonical_project = repo_root / "canonical" / canonical

    def _run_baseline(self, model: AIDCRoomModel, weather: AIDCWeatherProfile) -> SimulationResult:
        """运行基线仿真。

        对于 operation 任务，基线使用同一物理模型 + 固定策略。
        对于 co-design 任务，基线使用 canonical 默认模型 + 固定策略。
        """
        baseline_model = model
        if self.canonical_project and self.canonical_project.exists():
            try:
                room_id = self._detect_room_id(self.canonical_project)
                baseline_model = AIDCRoomModel.from_adl_project(self.canonical_project, room_id=room_id)
            except Exception:
                pass
        self._last_baseline_model = baseline_model
        baseline_strategy = make_baseline_strategy(self.simulation_hours)
        baseline_sim = AIDCSimulator(baseline_model, weather)
        return baseline_sim.run(baseline_strategy, hours=self.simulation_hours)

    def _find_strategy(self, workspace_root: Path, task: Any) -> Strategy:
        """从 workspace 寻找策略文件。"""
        # 优先查找 strategy.yaml / strategy.json
        for ext in [".yaml", ".yml", ".json"]:
            sp = workspace_root / f"strategy{ext}"
            if sp.exists():
                return parse_strategy_file(sp, self.simulation_hours)

        # 检查 task metadata 中是否有嵌入式策略
        if hasattr(task, "metadata") and hasattr(task.metadata, "strategy"):
            return parse_strategy_file(Path(str(task.metadata.strategy)), self.simulation_hours)

        # Fallback: 从 task requirement 中的 JSON 块提取
        if hasattr(task, "metadata") and hasattr(task.metadata, "requirement"):
            req = task.metadata.requirement
            # 尝试寻找 ```json ... ``` 块中内嵌的策略
            import re
            m = re.search(r'```(?:json|yaml)?\s*\n(.*?)\n```', req, re.DOTALL)
            if m:
                try:
                    import yaml
                    data = yaml.safe_load(m.group(1))
                    if isinstance(data, dict) and ("decisions" in data or "templates" in data):
                        return parse_strategy_dict(data, self.simulation_hours)
                except Exception:
                    pass

        # 默认：基线策略
        return make_baseline_strategy(self.simulation_hours)

    def _load_model(self, task: Any, workspace_root: Path | None = None) -> AIDCRoomModel:
        """加载房间物理模型。

        优先级：workspace (co-design Agent 产出) > project_dir (canonical) > 默认路径。
        """
        # 1. Co-design 模式：Agent workspace 中有 rooms/DC-HALL-A.yaml
        room_files = list((workspace_root / "rooms").glob("*.yaml")) if workspace_root else []
        if workspace_root and room_files:
            try:
                room_id = room_files[0].stem
                return AIDCRoomModel.from_adl_project(workspace_root, room_id=room_id)
            except Exception:
                pass  # fall through

        # 2. 显式 canonical 项目路径
        if self.project_dir:
            room_id = self._detect_room_id(self.project_dir)
            return AIDCRoomModel.from_adl_project(self.project_dir, room_id=room_id)

        # 3. 从 task 获取
        if hasattr(task, "canonical_dir"):
            canonical_dir = Path(task.canonical_dir)
            room_id = self._detect_room_id(canonical_dir)
            return AIDCRoomModel.from_adl_project(canonical_dir, room_id=room_id)

        # 4. task l7_config 中指定的 canonical_project
        if self.canonical_project and self.canonical_project.exists():
            room_id = self._detect_room_id(self.canonical_project)
            return AIDCRoomModel.from_adl_project(self.canonical_project, room_id=room_id)

        # 5. 默认 SD-HWE-Bench canonical 目录
        import sd_hwe_bench
        bench_dir = Path(sd_hwe_bench.__file__).parent.parent.parent
        default_project = bench_dir / "canonical" / "datacenter-hall"
        if default_project.exists():
            room_id = self._detect_room_id(default_project)
            return AIDCRoomModel.from_adl_project(default_project, room_id=room_id)

        raise FileNotFoundError("Cannot find datacenter-hall ADL project")

    @staticmethod
    def _detect_room_id(project_dir: Path) -> str:
        """从项目 rooms 目录自动检测 room_id，回退到 DC-HALL-A。"""
        rooms_dir = project_dir / "rooms"
        if rooms_dir.exists():
            room_files = sorted(rooms_dir.glob("*.yaml"))
            if room_files:
                return room_files[0].stem
        return "DC-HALL-A"

    def _compute_score(
        self,
        result: SimulationResult,
        baseline: SimulationResult,
        lcc_agent: Any | None = None,
        lcc_baseline: Any | None = None,
    ) -> tuple[float, dict]:
        """计算归一化多目标得分。

        对每个目标：score = max(0, (baseline - result) / baseline)
        加权平均后减去约束违反罚分。
        """
        from sd_hwe_bench.simulation.lifecycle import LCCResult

        if self.objective == "lcc" and lcc_agent and lcc_baseline:
            return self._compute_lcc_score(lcc_agent, lcc_baseline)

        if self.objective == "combined" and lcc_agent and lcc_baseline:
            perf_score, perf_details = self._compute_performance_score(result, baseline)
            lcc_score, lcc_details = self._compute_lcc_score(lcc_agent, lcc_baseline)
            # 默认 50% performance + 50% LCC（可通过 objective_weights 调整）
            w_perf = self.objective_weights[0] if self.objective_weights else 0.5
            w_lcc = 1.0 - w_perf
            final = 0.5 * perf_score + 0.5 * lcc_score
            details = {
                "objective": self.objective,
                "final_score": round(final, 4),
                "performance": perf_details,
                "lcc": lcc_details,
            }
            return final, details

        return self._compute_performance_score(result, baseline)

    def _compute_performance_score(self, result: SimulationResult,
                                    baseline: SimulationResult) -> tuple[float, dict]:
        """计算运营性能得分。"""
        w_pue, w_carbon, w_water, w_cost = self.objective_weights

        # 各维度归一化得分（越低越好 → 得分越高）
        # 若 task 提供了 reference（已知最优/优秀解），则使用 (baseline - agent)/(baseline - reference)
        # 否则回退到 (baseline - agent)/baseline
        pue_ref = self.reference.get("avg_pue")
        carbon_ref = self.reference.get("total_carbon_kg")
        water_ref = self.reference.get("total_water_l")
        cost_ref = self.reference.get("total_cost_cny")

        pue_score = self._normalize_against_reference(baseline.avg_pue, result.avg_pue, pue_ref)
        carbon_score = self._normalize_against_reference(baseline.total_carbon_kg, result.total_carbon_kg, carbon_ref)
        water_score = self._normalize_against_reference(baseline.total_water_l, result.total_water_l, water_ref)
        cost_score = self._normalize_against_reference(baseline.total_cost_cny, result.total_cost_cny, cost_ref)

        weighted = (
            w_pue * pue_score
            + w_carbon * carbon_score
            + w_water * water_score
            + w_cost * cost_score
        )

        final_score = max(0.0, min(1.0, weighted))

        details = {
            "objective": self.objective,
            "weighted_score": round(weighted, 4),
            "final_score": round(final_score, 4),
            "breakdown": {
                "pue": {"agent": result.avg_pue, "baseline": baseline.avg_pue, "score": round(pue_score, 4)},
                "carbon_kg": {"agent": round(result.total_carbon_kg, 1), "baseline": round(baseline.total_carbon_kg, 1), "score": round(carbon_score, 4)},
                "water_l": {"agent": round(result.total_water_l, 0), "baseline": round(baseline.total_water_l, 0), "score": round(water_score, 4)},
                "cost_cny": {"agent": round(result.total_cost_cny, 2), "baseline": round(baseline.total_cost_cny, 2), "score": round(cost_score, 4)},
            },
            "weights": {
                "pue": w_pue, "carbon": w_carbon, "water": w_water, "cost": w_cost,
            },
        }
        return final_score, details

    def _compute_lcc_score(self, lcc_agent: Any, lcc_baseline: Any) -> tuple[float, dict]:
        """计算 LCC 得分：以 TCO 为主要指标。"""
        # TCO 越小越好
        baseline_tco = lcc_baseline.tco_cny
        agent_tco = lcc_agent.tco_cny
        tco_ref = self.reference.get("tco_cny")
        tco_score = self._normalize_against_reference(baseline_tco, agent_tco, tco_ref)

        # NPV 越小越好（NPV 为总成本净现值）
        baseline_npv = lcc_baseline.npv_cny
        agent_npv = lcc_agent.npv_cny
        npv_ref = self.reference.get("npv_cny")
        npv_score = self._normalize_against_reference(baseline_npv, agent_npv, npv_ref)

        # LCOE 越小越好
        baseline_lcoe = lcc_baseline.lcoe_cny_per_kwh
        agent_lcoe = lcc_agent.lcoe_cny_per_kwh
        lcoe_ref = self.reference.get("lcoe_cny_per_kwh")
        lcoe_score = self._normalize_against_reference(baseline_lcoe, agent_lcoe, lcoe_ref)

        weighted = 0.5 * tco_score + 0.3 * npv_score + 0.2 * lcoe_score

        final_score = max(0.0, min(1.0, weighted))

        details = {
            "objective": self.objective,
            "weighted_score": round(weighted, 4),
            "final_score": round(final_score, 4),
            "breakdown": {
                "tco_cny": {"agent": round(agent_tco, 2), "baseline": round(baseline_tco, 2), "score": round(tco_score, 4)},
                "npv_cny": {"agent": round(agent_npv, 2), "baseline": round(baseline_npv, 2), "score": round(npv_score, 4)},
                "lcoe_cny_per_kwh": {"agent": round(agent_lcoe, 4), "baseline": round(baseline_lcoe, 4), "score": round(lcoe_score, 4)},
            },
            "weights": {"tco": 0.5, "npv": 0.3, "lcoe": 0.2},
        }
        return final_score, details

    def _check_compliance(self, result: SimulationResult, lcc_agent: Any | None = None) -> dict:
        """检查硬约束是否满足。返回 {passed, violations, checks}。"""
        violations: list[str] = []
        checks: dict[str, Any] = {}

        # 温度约束
        max_temp_c = self.constraints.get("max_indoor_temp_c", 32.0)
        if hasattr(result, "max_indoor_temp_c") and result.max_indoor_temp_c is not None:
            temp_ok = result.max_indoor_temp_c <= max_temp_c
            checks["max_indoor_temp_c"] = {"value": result.max_indoor_temp_c, "limit": max_temp_c, "passed": temp_ok}
            if not temp_ok:
                violations.append(f"max_indoor_temp_c {result.max_indoor_temp_c:.2f} > {max_temp_c}")
        else:
            # Fallback: count temperature violations if no explicit max temp field
            checks["temp_violations"] = {"value": result.temp_violations, "limit": 0, "passed": result.temp_violations == 0}
            if result.temp_violations > 0:
                violations.append(f"temp_violations: {result.temp_violations}")

        # SOC 约束
        checks["soc_violations"] = {"value": result.soc_violations, "limit": 0, "passed": result.soc_violations == 0}
        if result.soc_violations > 0:
            violations.append(f"soc_violations: {result.soc_violations}")

        # PUE 约束：优先使用 task 显式约束，其次参考值，最后不回归基线
        pue_limit = self.constraints.get("max_pue")
        if pue_limit is None and self.reference.get("avg_pue") is not None:
            pue_limit = self.reference["avg_pue"]
        if pue_limit is not None:
            pue_ok = result.avg_pue <= pue_limit
            checks["avg_pue"] = {"value": result.avg_pue, "limit": pue_limit, "passed": pue_ok}
            if not pue_ok:
                violations.append(f"avg_pue {result.avg_pue:.4f} > {pue_limit}")

        passed = not violations
        return {"passed": passed, "violations": violations, "checks": checks}

    @staticmethod
    def _normalize(baseline: float, value: float) -> float:
        """归一化：baseline 为 0 分，0 为 1 分。"""
        if baseline <= 0:
            return 1.0
        return max(0.0, min(1.0, (baseline - value) / baseline))

    @staticmethod
    def _normalize_against_reference(baseline: float, value: float, reference: float | None) -> float:
        """使用 reference（最优）作为上界的归一化。

        - agent == baseline → 0 分
        - agent == reference → 1 分
        - agent < reference → 1 分（clip）
        """
        if reference is None:
            return PerformanceCritic._normalize(baseline, value)
        denom = baseline - reference
        if denom <= 0:
            return PerformanceCritic._normalize(baseline, value)
        return max(0.0, min(1.0, (baseline - value) / denom))
