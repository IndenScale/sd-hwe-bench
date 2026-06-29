# ADR 0006: 概念设计阶段的多方案比选评估

## 状态

已提出，2026-06-29。依赖 critic 注册表（见"相关决策"）。**分期 1（MVP）已实现**
（2026-06-29）：`conceptual-design` 任务品类 + `DecisionCritic` 档 1–3 + 任务
`tasks/telecom/aidc-scheme-selection-001/` 落地，参考方案通过 L0–L5 且决策分 1.0，
同场景重复评分逐字段一致（可复现性闸门通过）。档 4（理由 LLM-judge）与方案库扩展
留待分期 2/3。

## 背景

现有评估范式（L0–L5 piki 合规 + 单一 `solution/` 目录 + 对单条 `reference` 归一化的标量 `performance_score`）面向"唯一正确解"的任务：详细设计、EPC、运营优化都属此类——存在一个可仿真、可比对的目标解。

但工程的**概念设计阶段**不是这样工作的。概念设计的产物是**一组备选方案的比选**，而"最优方案"随项目场景而变，且**并非纯性能导向**。同一 60MW AIDC，在：

- 内蒙古（干冷气候、电价低、水配额紧）与广东（湿热、电价高、水充足）；
- 自有成熟供应链与依赖单一新供应商；
- 要求 2 年内可改造扩容与一次到位；

下的最优冷却/形态/配电/柴发方案可能完全不同。决策要综合**气候、水电价格、碳/水配额、供应商成熟度、中途换型灵活性、未来扩容空间**等多维度，其中多个维度非性能、不可由热/电仿真单独裁决。

当前框架无法表达也无法评估这种任务：`PerformanceCritic` 把单解与单基线比 PUE，既不接受多候选，也不接受"非性能权重"。本 ADR 定义概念设计比选任务的评估契约。

## 决策

### 1. 新增任务品类 `conceptual-design`

在 `TaskType` 中新增 `conceptual-design`（注意：`TaskType` 为 pydantic 严格枚举，新增值需同步改 `task.py`）。其评估**不复用** `aidc-performance`，而经 critic 注册表绑定到新的 `DecisionCritic`（见决策 5）。

### 2. 场景参数化（任务输入）

`task.yaml` 新增 `scenario:` 块，作为 Agent 必须响应的设计输入：

```yaml
scenario:
  climate: {dry_bulb_profile: ..., wet_bulb_profile: ..., extreme_high_c: 42}
  tariff: {peak: 1.05, flat: 0.65, valley: 0.35}     # 元/kWh
  water_price_cny_per_m3: 8.0
  water_quota_m3_per_year: 120000
  carbon_quota_t_per_year: 50000
  supplier_maturity: {liquid-cooling: 0.6, container: 0.9, ...}  # 0–1 显式标量
  flexibility_weight: 0.15        # 中途换型/扩容灵活性在决策中的权重
  criteria_weights: {pue: 0.25, capex: 0.2, water: 0.15, carbon: 0.15, flexibility: 0.15, supplier_risk: 0.1}
```

**关键**：所有非性能因素（供应商成熟度、配额松紧、灵活性）以**显式标量**给入，使加权决策可确定、可复现，而非依赖主观判断。

### 3. 方案设计空间分类法

候选方案沿以下正交维度组合（用户域定义）：

| 维度 | 取值 |
|---|---|
| 冷却 | 液冷 / 风冷 / 混合 |
| 机房形态 | 开放机柜 / 微模块 / 集装箱 / 方舱 |
| 散热 | 开式冷却塔 / 闭式 / 干冷 |
| 配电 | 变压方舱化 / 设备柜 |
| 柴发 | 柴发一体 / 分离 |

### 4. 提交契约

Agent 在 workspace 产出：

- `schemes/<scheme-id>/`：每个候选方案的可行 ADL 设计（或参数化描述符）。
- `comparison.yaml`：比选矩阵（准则 × 方案）+ 每格指标取值。
- `recommendation.yaml`：推荐方案 id + 结构化理由。

### 5. 评估方法 `DecisionCritic`（四档，绑定 L4）

1. **各方案可行性（门槛）**：每个候选过 L0–L3 piki（必要时 L4 仿真）。不可行方案不得进入比选/推荐。
2. **比选矩阵正确性**：矩阵中可计算指标（CAPEX/PUE/水耗/工期等）须与 bench 对该方案的**自有确定性仿真**在容差内一致——反"拍脑袋填表"。
3. **决策质量（核心）**：给定 `scenario.criteria_weights`，推荐方案须落在 Pareto 前沿、或为加权准则最优；按**排名距离**给部分分（推荐第 k 优得递减分）。
4. **理由质量（诊断）**：LLM-judge rubric 评推荐理由是否引用了场景关键约束，仅作诊断、不决定 passed。

`passed` 由档 1–3 的硬条件决定；档 4 与归一化总分进入诊断性 `performance_score`。

### 6. 参考模型：方案库而非单解

任务携带 `scheme_library`：bench 预计算的**逐方案确定性准则**（性能类由仿真得出，成本类由 LCC 得出），以及"场景 → 最优方案"的映射（或一个可复算的加权评分函数）。

可复现性保证：

- 性能/成本准则由 bench 引擎确定性计算，不依赖 Agent 自报；
- 非性能准则（供应商成熟度、配额）由 `scenario` 显式标量给入；
- 因此"哪个方案最优"在给定场景下是**确定且可复算**的，评分不依赖评审主观判断。

### 7. 层归属与注册表接入

`conceptual-design` 的 L4 由注册表解析为 `DecisionCritic`：

```yaml
# task.yaml
evaluation:
  - {critic: decision, layer: L4, provides_performance: true}
```

`DecisionCritic` 在 `CRITIC_BUILDERS` 注册（`src/sd_hwe_bench/critics/registry.py`），**无需改 `scorer.py`**——这正是 critic 注册表重构（见相关决策）要解锁的能力。

## 结果

### 正面

- 让 benchmark 覆盖工程实践中最具判断力的环节（方案比选），而非只考"把已知解填对"。
- "决策质量"评估是超越 pass/fail 的贡献点，具论文价值。
- 与 critic 注册表解耦后，新品类不触碰评分核心。

### 负面 / 风险

- **"最优方案"客观性**：靠"确定性准则 + 显式场景权重 + Pareto/加权评分"压制主观性，但场景权重本身的设定仍是命题设计责任。
- **方案空间组合爆炸**：5 维全组合达数十种。缓解：每个任务固定小方案库（如 3 冷却 × 2 形态 = 6 方案）。
- **LLM-judge 方差**：仅用于诊断性理由分，不进入 passed。
- **bench 仿真覆盖**：集装箱/方舱/干冷等形态需扩展现有 RC 热模型与 LCC 参数，否则无法确定性算准则。

### 分期

1. **MVP**（✅ 已实现 2026-06-29）：1 个 `conceptual-design` 任务，固定 6 方案小库
   （3 冷却 × 2 形态，其一因超水配额不可行）+ 显式 `scenario`，实现 `DecisionCritic`
   档 1–3，验证同一场景重复评分完全一致（可复现性闸门）。落地于
   `src/sd_hwe_bench/critics/decision.py`、`tasks/telecom/aidc-scheme-selection-001/`、
   `tests/test_decision_critic.py`。
2. 加档 4（理由 LLM-judge，诊断）。
3. 扩展方案库维度与对应仿真参数；多场景变体（同一物理题、不同 `scenario`）形成一组任务。

## 相关决策

- `docs/adr/0001-task-generation-strategy.md`：任务生成策略。
- `docs/adr/0003-task-extraction-tooling.md`：任务元数据 schema。
- `docs/adr/0004-commit-granularity-and-task-types.md`：任务分类。
- **Critic 注册表重构**（本次随附实现）：`src/sd_hwe_bench/critics/registry.py` + `task.yaml` 的 `evaluation:` 块，是 `DecisionCritic` 的接入点。

## 参考

- 现有 AIDC 设计任务：`tasks/telecom/aidc-60mw-001/`（单解 co-design，本 ADR 的前身）。
- 仿真/LCC 引擎：`src/sd_hwe_bench/simulation/`。
