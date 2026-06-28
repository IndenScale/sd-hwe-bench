# SD-HWE-Bench Agent Instructions

本文件记录 SD-HWE-Bench 项目当前阶段的关键概念、目标与开发约定。最后更新：2026-06-28（v6：评分层体系统一 + 论文/文档同步）。

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
| M4. 论文 A 定稿 | EaC 概念论文 | arXiv PDF 已生成；FSE 缩写版待写 | ✅ arXiv done |
| M5. 论文 B 定稿 | SD-HWE-Bench 实验论文 | 中文初稿更新 37 task + L0–L6 层体系 + v6 文档/论文同步；英文待翻译 | ✅ 本次更新 |
| M6. 投稿与发表 | 按目标刊物投稿 | 未开始 | 未开始 |

**术语体系**：统一使用 **Engineering as Code（EaC）** 作为顶层范式；**ADL** 作为设计语言；**Part** 作为工程原子（对应 piki Instance）；**ACC** 指代事后合规检查路径；**ASA** 指代装配体静态分析（L3），**ADA** 指代装配体动态分析（L4）。

---

## 1. 当前状态（2026-06-28 v6：评分层体系统一 + 论文/文档同步）

### 1.1 代码库

- **任务集**：37 个 telecom 任务
  - 16 阶段式 commit 任务：4 telecom-rack + 5 datacenter + 7 telecom-site
  - 5 POC 手工任务（comprehensive/connection/instance/layout/mating）
  - 5 复合 easy（telecom-easy-compound-001~005）
  - 4 涌现约束（telecom-emergent-001~004）
  - 3 跨专业综合（telecom-cross-001~003）
  - 4 AIDC 任务：aidc-operation-001/002、aidc-co-design-001/002
- **源码**：`src/sd_hwe_bench/` ~45 个 Python 文件，~7600 行
- **CLI**：6 个命令（`list` / `run` / `run-repair` / `score` / `archive` / `leaderboard`）
- **Actor**：4 种——`kimi` / `codex` / `openai`（含 `deepseek` 别名）
- **Critic**：L0(Syntax) / L1(Schema) / L2(Reference Integrity) / L3(Static Constraints) / L4(Reduced-Order Dynamic Model) / L5(Geometry Interference) / L6(FEM/CFD reserved) / Deliverable(critical, non-layer) / Performance Score(diagnostic) / Rubric(LLM-judge)
- **Container**：镜像 `sd-hwe-bench-piki:latest` 已构建（1.58GB）
- **测试**：118 passed, 2 skipped

### 1.2 v5 改进要点

**60MW AIDC 模型**：新增 `canonical/datacenter-hall-60mw/`

- 200 台机柜，1000 台 60kW 液冷 AI 服务器，总 TDP 60MW
- 8×10MW 离心式冷水机组（可缩放至 6-8 台）
- 20MWh 储能、5MWp 光伏、双路 40MVA 变压器
- 分时电价、湿球温度、变压器效率曲线

**AIDC 仿真引擎升级**（`src/sd_hwe_bench/simulation/`）

- 变压器效率随负载率变化
- 冷却液泵/风机功耗（风冷/液冷区分）
- 分时电价与电网碳强度
- 湿球温度驱动的免费冷却模型
- 冷冻水设定点影响 COP（越高 COP 越高）

**全生命周期成本模型**（`src/sd_hwe_bench/simulation/lifecycle.py`）

- CAPEX：冷却、变压器、储能、光伏、机柜、土建
- OPEX：电费、水费、维护费
- 收益：IT 负载租金 / GPU 折旧
- NPV / TCO / LCOE 计算

**L4 AIDC 仿真合规**（`src/sd_hwe_bench/critics/performance.py`）

- 支持 `objective: performance | lcc | combined`
- 支持 `reference` 作为最优解参考，避免 baseline 归一化天花板
- 自动检测 room_id，支持多 canonical 项目

### 新增任务

- `tasks/telecom/aidc-operation-002/`：60MW 运营优化（hard）
  - 基线 PUE 1.27，优化后 PUE 1.20（-5.3%）
- `tasks/telecom/aidc-co-design-002/`：60MW 设计-调度联合优化（hard）
  - 目标：TCO 最小化 + PUE ≤ 1.22
  - 基线 TCO ¥4785M，优化后 TCO ¥4363M（-8.8%）

### 1.3 实验数据（30-task 已评测）

| Model | Actor | Pass@1 | Avg Score | 任务覆盖 |
|---|---|---|---|
| Kimi k2.7 | CLI (kimi) | 84.7% (127/150) | 82.8% | 30 tasks |
| DeepSeek-v4-Pro | CLI (codex) | 86.7% (130/150) | 80.3% | 30 tasks |

60MW AIDC 新任务已部分评测（aidc-operation-002 / aidc-co-design-002）。

### 1.4 论文

| 论文 | 位置 | 状态 |
|------|------|------|
| A: EaC 概念篇 | `papers/engineering-as-code/` | arXiv PDF 完成；FSE 缩写版待做 |
| B: SD-HWE-Bench 实验篇 | `papers/sd-hwe-bench/` | 37-task + L0–L6 层体系 + v6 文档/论文同步完成；英文待翻译 |

---

## 2. 下一步优先级

### 2.1 当前会话完成（2026-06-28）

| 产出 | 说明 |
|------|------|
| `docs/` | 文档重组 + `evaluation/scoring.md` v6 评分规则同步 |
| `papers/sd-hwe-bench/src/sections-zh/` | 论文全部 sections 与附录同步到 L0–L6 新体系、37 任务统计、30-task 实验结果 |
| `scripts/assemble_paper.py` | 聚合脚本常量与摘要更新为当前 37/30 task、2 model 数据 |
| `AGENTS.md` | 当前状态与任务统计同步到 v6 |
| `canonical/datacenter-hall-60mw/` | 60MW AIDC 高精度 ADL 项目 |
| `src/sd_hwe_bench/simulation/` | 仿真引擎升级：变压器、泵、分时电价、湿球温度、设定点-COP |
| `src/sd_hwe_bench/simulation/lifecycle.py` | 全生命周期成本模型（CAPEX/OPEX/NPV/TCO/LCOE） |
| `tasks/telecom/aidc-operation-002/` | 60MW 运营优化任务（PUE 区分度 5.3%） |
| `tasks/telecom/aidc-co-design-002/` | 60MW 设计-调度联合优化任务（TCO 区分度 8.8%） |
| `src/sd_hwe_bench/critics/performance.py` | L4 AIDC 仿真合规：硬约束检查 + performance_score 诊断 |
| `tests/test_aidc_simulation_60mw.py` | 60MW + LCC 单元测试 |
| `scripts/verify_aidc_benchmark.py` | 端到端验证脚本更新 |

### 2.2 下个会话推进

1. **AIDC 仿真实验**
   - 在 60MW 新任务上运行 flash/codex/kimi pass@1
   - 更新 leaderboard/results.json

2. **论文 B 英文版**
   - 将 v5 AIDC 结果翻译成英文 sections
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
| canonical/datacenter-hall | 2 | AIDC 14.8kW 运营与设计-调度联合优化 |
| canonical/datacenter-hall-60mw | 2 | 60MW AIDC 高精度模型 |
| canonical/telecom-site | 7 | 户外基站，天线/RRU/防雷/馈线/结构/热管理/频谱 |

### 3.2 任务结构

```text
tasks/<domain>/<task-name>/
├── task.yaml          # TaskMetadata（含 scoring_layers, l7_config）
├── scaffold/          # Agent 可见初始项目
├── solution/          # 参考方案（Agent 不可见）
└── expected/          # 期望交付物（可选）
```

### 3.3 评分层

L0(Syntax) → L1(Schema) → L2(Reference Integrity) → L3(Static Constraints) → L4(Reduced-Order Dynamic Model) → L5(Geometry Interference) → L6(FEM/CFD reserved) → Deliverable(critical, non-layer) → Performance Score(diagnostic) → Rubric(LLM)

权重：L0=0%, L1=10%, L2=15%, L3=40%, L4=15%, L5=20%；交付物与性能分数不占层权重

---

## 4. CLI 速查

```bash
sd-hwe-bench list [--domain telecom]
sd-hwe-bench run <task-id|prefix> --actor <spec> [--passes N] [--jobs N] [--sandbox docker]
sd-hwe-bench run-repair <task-id> --actor <spec> [--max-repair N]
sd-hwe-bench score <task-id> <output-dir> [--sandbox docker]
sd-hwe-bench archive [--format json]
sd-hwe-bench leaderboard [--update]
```

---

## 5. 开发约定

- 测试目标：保持 ≥110 tests 通过
- 新增任务含完整 `task.yaml`、`scaffold/`、`solution/`
- 所有 solution 必须通过 `piki check`
- `scoring_layers` 可从 task.yaml 覆盖
- AIDC 任务需在 `l7_config` 中提供 `reference` 以支持合理 score 区分度
- 实验数据归档到 `runs/`
- 论文源文件在 `papers/*/src/`；`dist/` 为生成产物
- **论文编译**：`dist/draft-full.zh.md` 由 sections 源文件通过 `scripts/assemble_paper.py` 聚合生成，禁止手写占位符。修改 section 后运行 `uv run scripts/assemble_paper.py` 即可更新。所有数字必须来自代码库实测数据
