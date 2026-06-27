# SD-HWE-Bench Agent Instructions

本文件记录 SD-HWE-Bench 项目当前阶段的关键概念、目标与开发约定。最后更新：2026-06-27（v2 改进：46-task，L2 子层拆分，涌现约束+跨专业综合任务）。

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
| M2. 任务集扩展与框架稳定 | 34 任务，接口稳定 | ✅ | ✅ 已完成 |
| M3. 基准实验与 Leaderboard | 全量实验，可发表 Leaderboard | 34-task pass@1 完成；Actor Gap 发现已写入论文 | 🟡 pass@1 done；v2 改进待重跑 |
| M3b. v2 改进 | 诊断+修复区分度不足 | 46-task，L2 拆分，涌现+跨专业任务就绪 | ✅ 已完成 |
| M4. 论文 A 定稿 | EaC 概念论文 | arXiv PDF 已生成；FSE 缩写版待写 | ✅ arXiv done |
| M5. 论文 B 定稿 | SD-HWE-Bench 实验论文 | 中文初稿更新 34→46 task + L2 拆分 | ✅ 本次更新 |
| M6. 投稿与发表 | 按目标刊物投稿 | 未开始 | 未开始 |

**术语体系**：统一使用 **Engineering as Code（EaC）** 作为顶层范式；**ADL** 作为设计语言；**Part** 作为工程原子（对应 piki Instance）；**ACC** 指代事后合规检查路径；**ESA** 指代 EaC 的工程静态分析。

---

## 1. 当前状态（2026-06-27 v2 改进完成）

### 1.1 代码库

- **源码**：`src/sd_hwe_bench/` 39 个 Python 文件，~6800 行
- **CLI**：6 个命令（`list` / `run` / `run-repair` / `score` / `archive` / `leaderboard`）
- **任务集**：46 个 telecom 任务
  - 29 canonical-extracted：15 telecom-rack + 8 datacenter + 6 telecom-site
  - 5 POC 手工任务（comprehensive/connection/instance/layout/mating）
  - 5 复合 easy（telecom-easy-compound-001~005）：递增依赖链，3-4 实例起步
  - 4 涌现约束（telecom-emergent-001~004）：约束不显式声明，从 scaffold 推断
  - 3 跨专业综合（telecom-cross-001~003）：电气+结构+消防多域约束
- **Actor**：4 种——`kimi` / `codex` / `gemini` / `openai`（含 `deepseek` 别名）
- **Critic**：L0(Syntax) / L1+L2a+L2b+L2c+L3+L4(Piki) / L5/L6(Deliverable) / Rubric(LLM-judge)
- **Container**：镜像 `sd-hwe-bench-piki:latest` 已构建（1.58GB）
- **测试**：110/124 pass（14 个 actor/parallel 测试需 actor 环境）

### 1.2 v2 改进要点

**L2 评分层拆分**：16 条 piki 规则从单层 L2 拆分为三个子层，避免连锁失败：
| 子层 | 规则数 | 语义 | 权重 |
|------|--------|------|------|
| L2a | 5 | 标识与外键完整性（REFS, FK, TELECOM-FK, TAGS） | 5% |
| L2b | 7 | 接口与端口兼容性（INTERFACE, TELECOM-PORT, TELECOM-CONN） | 5% |
| L2c | 4 | 配合与目录约束（MATE, CATALOG） | 5% |

**Prompt 增强**：API Actor prompt 显式警告 `capacity_w` vs `power_capacity_w` 字段名陷阱。

**任务难度重标定**：
| 难度 | 改进前 | 改进后 |
|------|--------|--------|
| easy | 17 (50%) | 18 (39%) |
| medium | 13 (38%) | 21 (46%) |
| hard | 4 (12%) | 7 (15%) |

### 1.3 实验数据（34-task baseline，46-task 待重跑）

| Model | Actor | Pass@1 | Avg Score | 任务覆盖 |
|---|---|---|---|---|
| Kimi k2.7 | CLI | 100% (20/20) | 89% | 20 tasks |
| DeepSeek-v4-Flash | CLI (codex) | 100% (15/15) | 88% | 15 新增 |
| DeepSeek-v4-Pro | CLI (codex) | 100% (15/15) | 88% | 15 新增 |
| DeepSeek-v4-Flash | API | 80% (16/20) | 82% | 20 old |
| DeepSeek-v4-Pro | API | 90% (18/20) | 84% | 20 old |

**Actor Gap**：CLI Actor 系统性优于 API Actor（+10-20pp）。根因：文件系统交互、YAML 解析损耗。

**API Actor 共同失败模式**：L2a（引用完整性）> L3（工程约束）> L1（Schema）。

### 1.4 论文

| 论文 | 位置 | 状态 |
|------|------|------|
| A: EaC 概念篇 | `papers/engineering-as-code/` | arXiv PDF 完成；FSE 缩写待做 |
| B: SD-HWE-Bench 实验篇 | `papers/sd-hwe-bench/` | 46-task + L2 拆分更新完成；英文待翻译 |

---

## 2. 下一步优先级

1. **重跑 46-task 全量实验**（含 L2a/L2b/L2c 分层评分）
2. **pass@5 + repair ablation**
3. **扩展模型覆盖**：GPT-4.1、Gemini 2.5、Claude 4
4. **论文 B 英文版**
5. **论文 A FSE 缩写版**

### 已识别的局限（v2 部分解决）

1. ~~Easy 任务占比 50%~~ → 39%，且 5 个复合 easy 增加依赖链深度
2. ~~L2 单层过载~~ → 拆分为 L2a/L2b/L2c 三个子层
3. Actor Gap 未被社区标准化——仍存在
4. pass@5 和 repair ablation 缺失——待跑
5. 涌现约束任务仅 4 个——可继续扩展

---

## 3. 关键概念

### 3.1 Canonical Project 与任务提取

| 工程 | 任务数 | 领域 |
|------|--------|------|
| canonical/telecom-rack | 15 | 42U 机柜扩容，PDU/设备/光纤/跨机柜 |
| canonical/datacenter | 8 | 数据中心机房，ToR 组网，地板载荷 |
| canonical/telecom-site | 6 | 户外基站，天线/RRU/防雷/馈线 |

### 3.2 任务结构

```text
tasks/<domain>/<task-name>/
├── task.yaml          # TaskMetadata（含 scoring_layers）
├── scaffold/          # Agent 可见初始项目
├── solution/          # 参考方案（Agent 不可见）
└── expected/          # 期望交付物（可选）
```

### 3.3 评分层

L0(YAML syntax) → L1(Schema) → L2a(Identity/FK) → L2b(Interface/Port) → L2c(Mate/Catalog) → L3(Power/Lifecycle) → L4(Rack/Collision) → L5/L6(Deliverable) → Rubric(LLM)

权重：L1=10%, L2a=5%, L2b=5%, L2c=5%, L3=40%, L4=20%, Deliverable=15%

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
- `scoring_layers` 可从 task.yaml 覆盖（如 compound-001 不含 L3）
- 实验数据归档到 `runs/`
- 论文源文件在 `papers/*/src/`；`dist/` 为生成产物
