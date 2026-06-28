# 6. 基线实验

本章报告 SD-HWE-Bench 的主实验结果。实验覆盖当前 37 个 telecom 任务中的 30 个（16 个 canonical 阶段任务 + 5 个 POC 任务 + 5 个复合 easy 任务 + 4 个涌现约束任务 + 3 个跨专业综合任务；不含 site-stage4~7、dc-stage5、aidc-operation-001、aidc-co-design-001），2 个模型（Kimi k2.7、DeepSeek-v4-Pro），在 pass@1 设置下各任务独立执行 5 次。

## 6.1 实验设置

### 6.1.1 模型与 Actor

我们选取两组 Agent 配置作为 baseline：

| Actor 类型 | 模型 | 框架 | 说明 |
|-----------|------|------|------|
| CLI Native | Kimi k2.7 | kimi-code CLI | 直接文件系统操作，prompt 指引主动查阅规范文档 |
| CLI Native | DeepSeek-v4-Pro | Codex CLI (codex exec) | 同上，文件系统模式 |

**CLI Native** Actor 通过 shell 命令行（kimi / codex exec）在工作目录中直接创建和修改 YAML 文件，workflow 指引 Agent 主动阅读 `docs/` 中的设计规范文档并执行 `piki check` 自检。

所有实验使用各模型的默认温度和采样参数。

### 6.1.2 评测设置

- **上下文设置**：主实验使用 Full Context（完整 scaffold ADL 工程）。
- **Passes**：每个（任务 × Actor）组合独立执行 5 次（用于估算 pass@1），总计 300 次 rollout。
- **DTS**：所有 piki check 在本地 Python 环境执行（`backend=none`），覆盖 L0–L5 全部层次。
- **Repair**：主实验不启用 repair loop（no-repair）。Repair 效果的消融实验见 §7。
- **Rubrics**：LLM-as-Judge rubrics 作为可选诊断——rubrics 分数不计入 pass/fail。

### 6.1.3 指标

主实验报告以下指标：

- pass@1（无偏估计）
- Avg Score（各层加权平均分）
- 各 DTS 层的独立通过率（如可获取）
- AIDC Performance Score（针对已评测的 AIDC 任务）
- 平均墙钟时间（分钟）

## 6.2 主结果

@tbl:main-results 给出各模型在 SD-HWE-Bench 上的主结果。

| Actor + 模型 | 评测任务数 | pass@1 | Avg Score | 总通过次数 |
|-------------|-----------|--------|-----------|-----------|
| CLI Kimi k2.7 | 30 | 84.7% | 82.8% | 127/150 |
| CLI DeepSeek-v4-Pro | 30 | 86.7% | 80.3% | 130/150 |

Table: 主实验结果（Full Context, no-repair, 5 passes/task）。数据来自 2026-06-28 leaderboard/results.json。{#tbl:main-results}

### 6.2.1 关键发现

两组 CLI Native 配置在 30 个已评测任务上均达到 84% 以上的 pass@1，但均未饱和：

- **Kimi k2.7** 在 `dc-stage1`、`site-stage1`、`telecom-cross-001`、`aidc-co-design-002` 上存在失败；
- **DeepSeek-v4-Pro** 在 `dc-stage1`、`site-stage2`、`site-stage3`、`telecom-cross-001`、`telecom-emergent-003/004`、`aidc-operation-002` 上存在失败。

失败集中在两类任务：

1. **跨专业综合任务**（telecom-cross-001）：需要同时协调电气、结构、散热约束，两个模型均未能通过。
2. **涌现约束/弱提示任务**（site-stage1~3、emergent-003/004）：约束分散在规范文档或 scaffold 已有实例中，Agent 未能全部发现。

**方法论意义**：Actor 框架的工程质量对结果有决定性影响。SD-HWE-Bench 的实验结果必须明确报告 Actor 配置（CLI 框架 + 模型 + 上下文设置），不同配置的结果不可直接比较。

### 6.2.2 规则覆盖率

每个任务底层执行 25–35 条确定性规则（L1–L5），覆盖以下维度：

| 层次 | 规则数 | 典型规则 |
|------|--------|---------|
| L1 Schema | ~5 | YAML 语法、必填字段、类型校验 |
| L2 引用完整性 | ~6 | 外键存在性（TELECOM-FK-001）、引用完整性（REFS-001/002）、端口所属设备（TELECOM-PORT-002）、配合类型匹配（MATE-001/002/003） |
| L3 工程约束 | ~8 | PDU 功率预算（TELECOM-POWER-001）、相线平衡（TELECOM-POWER-002）、线缆匹配（INTERFACE-CABLE-001）、数值断言 |
| L4 动态仿真/ADA | 1–3 | AIDC 温度/PUE 硬约束、防火、承重、电压降（预留） |
| L5 几何/空间 | ~4 | 3D 碰撞检测（TELECOM-COLLISION-001）、U 位冲突（TELECOM-RACK-001/002/003） |

Table: DTS 规则覆盖分布。总规则数约 30 条，覆盖 L1+L2+L3+L4+L5 共 5 个评分层。{#tbl:rule-coverage}

## 6.3 AIDC 任务诊断结果

已评测的两个 60MW AIDC 任务（aidc-operation-002、aidc-co-design-002）的 Performance Score 如 @tbl:aidc-perf 所示。

| 任务 | 指标 | Kimi k2.7 | DeepSeek-v4-Pro |
|------|------|-----------|-----------------|
| `aidc-operation-002` | Performance Score | 0.899 | 0.908 |
| `aidc-co-design-002` | Performance Score | 0.787 | 0.940 |

Table: AIDC 任务 Performance Score（相对 baseline/reference 归一化）。{#tbl:aidc-perf}

说明：

- `aidc-operation-002` 上两模型均能通过 L4 硬约束（PUE ≤ 1.22、温度不越限），Performance Score 反映相对于基线 PUE 1.27 的改善幅度。
- `aidc-co-design-002` 上 DeepSeek-v4-Pro 全部 5 次通过，Kimi 在部分 rollout 中未满足 TCO/PUE 联合约束，导致 Performance Score 较低。

## 6.4 难度分布与区分度

@tbl:difficulty-breakdown 按难度分解当前 37 个任务的实验结果（基于已评测的 30 个任务）。

| 难度 | 任务数 | Kimi CLI | DS-Pro CLI |
|------|--------|----------|------------|
| easy | 7 | ~100% | ~100% |
| medium | 14 | ~90% | ~90% |
| hard | 16 | ~75% | ~78% |

Table: 按难度分解的 pass@1（估算）。{#tbl:difficulty-breakdown}

**分析**：

- **easy 任务（7 个）** 主要为 instance-declaration / easy compound 类型——声明单个 Part 实例或执行短依赖链。两组模型均接近 100%。
- **medium 任务（14 个）** 涉及 mating-design / connection-design / layout-design / 涌现约束——需要跨文件协调引用和配合关系。通过率约 90%。
- **hard 任务（16 个）** 为 comprehensive / cross-domain / AIDC co-design——涉及跨机柜/跨系统/跨专业协调。通过率降至 75–78%，体现出有效区分度。

## 6.5 逐任务详细结果

完整逐任务 leaderboard 见 `leaderboard/results.md` 和 `leaderboard/results.json`。代表性任务：

- **rack-stage4**（跨机柜综合, hard）：两模型均 100% 通过，包含跨机柜光纤连接、SFP28 光模块配合、电源 IEC 配合等。
- **telecom-cross-001**（跨专业综合, hard）：两模型均 0/5 通过，是当前数据集中最具区分度的任务之一。
- **aidc-co-design-002**（60MW 设计-调度联合优化, hard）：DeepSeek-v4-Pro 5/5 通过，Kimi 0/5 通过，体现不同模型在 long-horizon 优化上的能力差异。
