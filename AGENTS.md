# SD-HWE-Bench Agent Instructions

本文件记录 SD-HWE-Bench 项目当前阶段的关键概念、目标与开发约定。最后更新：2026-06-29（v7.1：concept-design DecisionCritic MVP 落地 / ADR 0006 分期 1）。

## 全局约束

- **禁止使用 `pip`、`pipx`、`npm`、`npx`、`yarn`、`pnpm` 命令**。Python 依赖管理统一使用 `uv`（`uv sync` / `uv pip install` / `uv run` 等）。

---

## 0. 北极星目标

> **完成 SD-HWE-Bench 的写作并发表。**

### 0.1 WBS 与里程碑

| 里程碑 | 目标 | 完成标准 | 当前状态 |
|---|---|---|---|
| M0. 发表目标锁定 | 确定分篇发表策略、目标会议/期刊 | ✅ | ✅ 已完成 |
| M1. POC 跑通 | 5 个 telecom 任务流程闭环 | ✅ | ✅ 已完成 |
| M2. 任务集扩展与框架稳定 | 37 任务，接口稳定 | ✅ | ✅ 已完成 |
| M3. 基准实验与 Leaderboard | 全量实验，可发表 Leaderboard | 30-task 评测 Kimi/DeepSeek pass@1 84.7%/86.7% | ✅ 完成 |
| M3b. v2/v6 改进 | 诊断+修复区分度不足 | 37-task，L2 统一，涌现+跨专业+AIDC 任务就绪 | ✅ 已完成 |
| M3c. v7 AIDC 任务升级 | detailed-design + EPC 任务，施工排程/吊装/VDC | 4 个新 AIDC 任务（conceptual/detailed/EPC/edge） + Constructability/EPC critics | ✅ 本次更新 |
| M4. 论文 A 定稿 | EaC 概念论文 | arXiv PDF 已生成；FSE 缩写版待写 | ✅ arXiv done |
| M5. 论文 B 定稿 | SD-HWE-Bench 实验论文 | 中文初稿更新 37 task + L0–L6 层体系 + v6 文档/论文同步；英文待翻译 | ✅ 本次更新 |
| M6. 投稿与发表 | 按目标刊物投稿 | 未开始 | 未开始 |

**术语体系**：统一使用 **Engineering as Code（EaC）** 作为顶层范式；**ADL** 作为设计语言；**Part** 作为工程原子（对应 piki Instance）；**ACC** 指代事后合规检查路径；**ASA** 指代装配体静态分析（L3），**ADA** 指代装配体动态分析（L4）。

---

## 1. 当前状态（2026-06-28 v6：评分层体系统一 + 论文/文档同步）

### 1.1 代码库

- **任务集**：38 个 telecom 任务
  - 16 阶段式 commit 任务：4 telecom-rack + 5 datacenter + 7 telecom-site
  - 5 POC 手工任务（comprehensive/connection/instance/layout/mating）
  - 5 复合 easy（telecom-easy-compound-001~005）
  - 4 涌现约束（telecom-emergent-001~004）
  - 3 跨专业综合（telecom-cross-001~003）
  - 4 AIDC 任务：edge-dc-design-001、aidc-conceptual-design-001、aidc-detailed-design-001、aidc-epc-001
  - 1 概念设计多方案比选：aidc-scheme-selection-001（conceptual-design，DecisionCritic）
- **源码**：`src/sd_hwe_bench/` ~50 个 Python 文件，~8400 行
- **CLI**：7 个命令（`list` / `run` / `run-repair` / `score` / `archive` / `leaderboard` / `batch`）
- **Actor**：4 种——`kimi` / `codex` / `openai`（含 `deepseek` 别名）
- **Critic**：L0(Syntax) / L1(Schema) / L2(Reference Integrity) / L3(Static Constraints) / L4(Reduced-Order Dynamic Model / CPML Schedule / Multi-Scheme Decision) / L5(Geometry Interference + Constructability) / L6(FEM/CFD reserved) / Deliverable(critical, non-layer) / Performance Score(diagnostic) / Rubric(LLM-judge)
- **Container**：镜像 `sd-hwe-bench-piki:latest` 已构建（1.58GB）
- **测试**：145 passed, 2 skipped

### 1.2 v7 改进要点（当前版本）

#### AIDC 任务体系重构

- 退役原 `aidc-operation-001/002` 与 `aidc-co-design-001/002`（移至 `tasks/telecom/_legacy/`）。
- 新增 4 个 AIDC/数据中心任务，覆盖从 edge 到 60MW、从概念设计到施工建造的全生命周期：
  - `edge-dc-design-001`：medium 边缘数据中心设计-调度联合优化（`canonical/datacenter-hall`）。
  - `aidc-conceptual-design-001`：hard 60MW AIDC 概念设计-调度联合优化（`canonical/datacenter-hall-60mw`）。
  - `aidc-detailed-design-001`：hard 60MW AIDC 详细设计（`canonical/aidc-detailed`），包含吊装、临时道路、VDC 工作面等施工可建性检查。
  - `aidc-epc-001`：hard 60MW AIDC EPC 施工排程与风险响应（`canonical/aidc-detailed`），使用 CPML 施工排程模型。

**施工可建性 Critic**（`src/sd_hwe_bench/critics/constructability.py`）

- 检查每个重型设备（冷水机组、变压器等）是否配置吊装方案：起重机吨位 ≥ 1.25× 设备重量、作业半径、净空高度、吊点位置。
- 检查主吊车在设备到场至就位期间持续在场（租赁期覆盖最迟吊装日）。
- 检查至少两个 VDC（虚拟建造）工作面，含编号、区域、里程碑、前置条件。

**CPML/EPC 施工排程引擎**（`src/sd_hwe_bench/construction/`）

- `cpml.py` / `parser.py` / `scheduler.py`：活动、资源、天气、延迟、应急预案的 YAML 建模与离散事件调度。
- `events.py` / `evaluator.py`：20 组随机天气/供应链场景下的 SLA 鲁棒性评估。
- `EPCCritic`（`src/sd_hwe_bench/critics/epc.py`）：硬约束检查（工期 ≤ deadline、资源不超容、应急预案合法）+ Performance Score（P90 工期与成本）。

**详细设计 canonical 工程**（`canonical/aidc-detailed/`）

- 在 `datacenter-hall-60mw` 物理模型基础上增加：主机房建筑 geometry、架空地板、车辆通道、大门、机柜行列布局、`placed-on` 配合、冷水机组/变压器设备实体。
- 通过 `piki check`：30 passes，0 errors。

### 1.3 v6/v5 保留要点

**60MW AIDC 模型**：`canonical/datacenter-hall-60mw/` 提供 200 台机柜、1000 台 60kW 液冷 AI 服务器、8×10MW 冷水机组、20MWh 储能、5MWp 光伏、双路 40MVA 变压器、分时电价、湿球温度、变压器效率曲线。

**AIDC 仿真/LCC 引擎**：保留 RC 热网络、分时电价、湿球温度免费冷却、设定点-COP 曲线、CAPEX/OPEX/NPV/TCO/LCOE 全生命周期成本模型。

**L4 分支**：AIDC 设计任务走 `PerformanceCritic`（热/电/LCC 仿真），EPC 任务走 `EPCCritic`（施工排程仿真）。

### 1.4 实验数据

| Model | Actor | Pass@1 | Avg Score | 任务覆盖 |
|---|---|---|---|
| Kimi k2.7 | CLI (kimi) | 84.7% (127/150) | 82.8% | 30 tasks（旧 AIDC 任务） |
| DeepSeek-v4-Pro | CLI (codex) | 86.7% (130/150) | 80.3% | 30 tasks（旧 AIDC 任务） |

> 注：v7 新增 4 个 AIDC 任务尚未完成多模型 pass@1 实验，当前仅验证参考方案全通过。下一步需在 edge-dc-design-001 / aidc-conceptual-design-001 / aidc-detailed-design-001 / aidc-epc-001 上重跑 baseline。

### 1.5 论文

| 论文 | 位置 | 状态 |
|------|------|------|
| A: EaC 概念篇 | `papers/engineering-as-code/` | arXiv PDF 完成；FSE 缩写版待做 |
| B: SD-HWE-Bench 实验篇 | `papers/sd-hwe-bench/` | 37-task + L0–L6 层体系 + v7 AIDC 任务同步完成；英文待翻译 |

---

## 2. 下一步优先级

### 2.1 当前会话完成（2026-06-29 v7）

| 产出 | 说明 |
|------|------|
| `canonical/aidc-detailed/` | 60MW AIDC 详细设计 canonical，含 geometry、吊装条件、VDC 工作面 |
| `src/sd_hwe_bench/critics/constructability.py` | 施工可建性 Critic（吊装、主吊车租赁、VDC 工作面） |
| `tasks/telecom/aidc-detailed-design-001/` | hard detailed-design 任务，参考方案通过 L0–L5 |
| `src/sd_hwe_bench/construction/` | CPML 施工排程引擎（活动/资源/天气/延迟/应急预案/评估） |
| `src/sd_hwe_bench/critics/epc.py` | EPCCritic（工期、资源、应急预案 + 20 场景 SLA） |
| `tasks/telecom/aidc-epc-001/` | hard EPC 任务，参考方案通过 L0–L4 |
| `tasks/telecom/edge-dc-design-001/` | medium co-design 任务（`canonical/datacenter-hall`） |
| `tasks/telecom/aidc-conceptual-design-001/` | hard co-design 任务（`canonical/datacenter-hall-60mw`） |
| `src/sd_hwe_bench/task.py` | 新增 `EPC` / `DETAILED_DESIGN` 任务类型 |
| `src/sd_hwe_bench/scorer.py` | L4 按任务类型分支，L5 合并 ConstructabilityCritic |
| `tests/test_aidc_simulation_60mw.py` | 更新为 4 个新 AIDC 任务 + 原有仿真/LCC 测试 |
| `AGENTS.md` / `docs/evaluation/scoring.md` / `papers/` | 同步 v7 任务与评分体系 |

### 2.2 下个会话推进

1. **AIDC 新任务 baseline 实验**
   - 在 4 个新 AIDC 任务上运行 flash/codex/kimi pass@1
   - 更新 `leaderboard/results.json` 与 `runs/`

2. **论文 B 英文版**
   - 将 v7 AIDC 结果翻译成英文 sections
   - 更新 figures/tables

3. **论文 A FSE 缩写版**
   - 从 arXiv 版压缩至 10 页

4. **CPML 造价/排程基础设施**（跨项目）
   - 在 piki 仓库新建 CPML 子项目
   - ADL → CPML 编译器、排程求解器、LCC 建设成本

5. **pass@5 + repair ablation**

6. **故障注入任务**

### 已识别的局限（v5）

1. AIDC 仿真仍为集总参数 RC 模型，尚未引入 CFD/二维热模型
2. LCC 收益模型较简化（统一 IT 租金/显卡折旧）
3. CPML 代码尚未创建，当前 LCC 建设成本为简化估算
4. 未对 60MW 任务进行多模型实验

---

## 3. 关键概念

### 3.1 Canonical Project 与任务提取

| 工程 | 任务数 | 领域 |
|------|--------|------|
| canonical/telecom-rack | 4 | 42U 机柜扩容，PDU/设备/光纤/跨机柜 |
| canonical/datacenter | 5 | 数据中心机房，ToR 组网，地板载荷 |
| canonical/telecom-site | 7 | 户外基站，天线/RRU/防雷/馈线/结构/热管理/频谱 |
| canonical/datacenter-hall | 1 | AIDC 14.8kW 运营/设计-调度（edge-dc-design-001） |
| canonical/datacenter-hall-60mw | 1 | 60MW AIDC 概念设计-调度联合优化 |
| canonical/aidc-detailed | 2 | 60MW AIDC 详细设计 + EPC 施工排程 |
| （无 canonical，方案库内嵌 task.yaml） | 1 | 60MW AIDC 概念设计多方案比选（aidc-scheme-selection-001） |

### 3.2 任务结构

```text
tasks/<domain>/<task-name>/
├── task.yaml          # TaskMetadata（含 scoring_layers, l7_config）
├── scaffold/          # Agent 可见初始项目
├── solution/          # 参考方案（Agent 不可见）
└── expected/          # 期望交付物（可选）
```

### 3.3 评分层

L0(Syntax) → L1(Schema) → L2(Reference Integrity) → L3(Static Constraints) → L4(Dynamic Model / CPML Schedule) → L5(Geometry Interference + Constructability) → L6(FEM/CFD reserved) → Deliverable(critical, non-layer) → Performance Score(diagnostic) → Rubric(LLM)

权重：L0=0%, L1=10%, L2=15%, L3=40%, L4=15%, L5=20%；交付物与性能分数不占层权重。

**L4 按任务类型分支**：

- AIDC 设计任务（operation / co-design）：`PerformanceCritic` 执行热/电/LCC 仿真。
- EPC 任务（epc）：`EPCCritic` 执行 CPML 施工排程与风险响应仿真。
- 概念设计任务（conceptual-design）：`DecisionCritic` 执行多方案比选（可行性闸门 / 矩阵正确性 / Pareto + 加权决策质量），确定性可复现，见 ADR 0006。

**L5 合并几何与可建性**：

- piki 几何规则（碰撞、U 位、间距）继续作为 L5 基础。
- `ConstructabilityCritic` 对 detailed-design / epc 任务检查吊装方案、主吊车租赁、VDC 工作面。

---

## 4. CLI 速查

```bash
sd-hwe-bench list [--domain telecom]
sd-hwe-bench run <task-id|prefix> --actor <spec> [--passes N] [--jobs N] [--sandbox docker]
sd-hwe-bench run-repair <task-id> --actor <spec> [--max-repair N]
sd-hwe-bench score <task-id> <output-dir> [--sandbox docker]
sd-hwe-bench archive [--format json]
sd-hwe-bench leaderboard [--update]
sd-hwe-bench batch --matrix <matrix.yaml> [--dry-run] [--max-workers N]
```

---

## 5. 开发约定

- 测试目标：保持 ≥110 tests 通过
- 新增任务含完整 `task.yaml`、`scaffold/`、`solution/`
- 所有 solution 必须通过 `piki check`
- `scoring_layers` 可从 task.yaml 覆盖
- **分析型 critic（L4/L5）选择由 `src/sd_hwe_bench/critics/registry.py` 注册表驱动**：默认按 `task_type` 推导，可在 task.yaml 用 `evaluation:` 块显式覆盖（`{critic, layer, mode, provides_performance, params}`）。新增评分品类 = 注册一个 builder + 写 critic，不改 `scorer.py`。
- 批量实验用 `sd-hwe-bench batch --matrix <yaml>`（模型 × 任务矩阵），示例见 `scripts/batch/pass5.yaml`；旧的硬编码批量脚本已归档至 `scripts/legacy/`
- AIDC 设计任务需在 `l7_config` 中提供 `reference` 以支持合理 score 区分度；EPC 任务需在 `l7_config` 中提供 `deadline_days`、`resource_limits`、`contingency_policy` 等 CPML 参数；detailed-design 任务需包含 `construction/` 吊装与 VDC 交付物；conceptual-design 任务需在 `scenario` 提供 `criteria_weights` 与场景标量、在 `l7_config.scheme_library` 内嵌逐方案确定性准则与 `feasible` 标志（答案键，Agent 不可见），交付 `comparison.yaml` + `recommendation.yaml`
- 实验数据归档到 `runs/`
- 论文源文件在 `papers/*/src/`；`dist/` 为生成产物
- **论文编译**：`dist/draft-full.zh.md` 由 sections 源文件通过 `scripts/assemble_paper.py` 聚合生成，禁止手写占位符。修改 section 后运行 `uv run scripts/assemble_paper.py` 即可更新。所有数字必须来自代码库实测数据
