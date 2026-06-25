# 6. 基线实验

本章报告 SD-HWE-Bench 的主实验结果。在完整基准实验完成前，本章使用占位符标记需填入的数据。当前 POC 阶段覆盖 1 个领域（telecom）、5 个任务、3 个 Actor——这些初步数字作为参考，但不构成论文的最终基线。

## 6.1 实验设置

### 6.1.1 模型

我们选取四类主流 LLM Agent 作为 baseline：

| Harness（Agent 框架） | 模型 | 提供商 | 上下文窗口 |
|----------------------|------|--------|-----------|
| Kimi Code CLI | kimi-code/k2.7 | Moonshot AI | ~128K tokens |
| Codex CLI | deepseek-v4-pro | DeepSeek | ~128K tokens |

当前基线仅覆盖两组 Harness-模型组合——Kimi 和 DeepSeek 是目前在代码/工程生成评测中表现最强的主流模型。所有实验使用各模型的默认温度和采样参数。CLI Agent 直接在工作目录中创建/修改 YAML 文件，通过 prompt 中的工作流指引调用 `piki check` 和 `piki generate`。

### 6.1.2 评测设置

- **上下文设置**：主实验使用 Full Context（完整 scaffold ADL 工程）。
- **Passes**：每个（任务 × Actor）组合独立执行 5 次（pass@5）。
- **DTS**：所有 piki check 在容器化环境（Docker `sd-hwe-bench-piki:latest`）中执行，确保评分一致性。
- **Repair**：主实验不启用 repair loop（no-repair）。Repair 效果的消融实验见 §7。
- **Rubrics**：LLM-as-Judge rubrics 作为可选诊断——rubrics 分数不计入 pass/fail。

### 6.1.3 指标

主实验报告以下指标：

- pass@1 和 pass@5
- %Apply（Agent 成功生成并应用 patch 的比例）
- 各 DTS 层的独立通过率
- 平均 API 成本（USD）
- 平均墙钟时间（秒）

## 6.2 主结果

@tbl:main-results 给出各模型在 SD-HWE-Bench 上的主结果。

| Harness + 模型 | pass@1 | pass@5 | %Apply | L0 | L1 | L2 | L3/ASA | L4/ADA | Cost ($) | Time (s) |
|---------------|--------|--------|--------|----|----|----|--------|--------|----------|----------|
| Kimi Code + k2.7 | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [x.xx] | [xxx] |
| Codex + deepseek-v4-pro | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [x.xx] | [xxx] |

Table: 主实验结果（Full Context, no-repair, pass@5）。DTS 层通过率为各层的独立通过比例。{#tbl:main-results}

> **需填入数据**：完成全量实验后替换所有 `[xx.x]` 占位符。

### 6.2.1 POC 阶段初步观察（参考，非最终结果）

在 POC 阶段对 5 个 telecom 任务的初步测试中，我们观察到以下模式（仅供参考，样本量远不足以作为论文结论）：

- 三个 CLI Agent（kimi / gemini / codex:deepseek）均能完成基本的 ADL YAML 生成，但 L2（引用完整性）和 L3/ASA（静态分析层）的通过率普遍较低。
- 最常见的失败模式包括：(1) 引用了未在 PDL 中定义的 Part ID；(2) 端口类型不兼容（如将 C13 接到 C19）；(3) U 位重叠但未检查；(4) 功率预算超限。
- 这些失败并非源于 Agent "不会"——它们在 prompt 中被明确告知了规则——而是源于 Agent 无法在设计空间中一贯地满足所有约束。

## 6.3 上下文设置对比

@tbl:context-results 给出了三种上下文设置下的 pass@1 对比。

| Harness + 模型 | Full Context | Oracle Context | Collapsed Context |
|---------------|-------------|---------------|-------------------|
| Kimi Code + k2.7 | [xx.x] | [xx.x] | [xx.x] |
| Codex + deepseek-v4-pro | [xx.x] | [xx.x] | [xx.x] |

Table: 三种上下文设置的 pass@1 对比。{#tbl:context-results}

> **需填入数据**：完成全量实验后替换所有 `[xx.x]` 占位符。

预期趋势：

- **Oracle Context 应显著优于 Full Context**：说明"定位正确修改模块"是核心瓶颈——与 SWE-bench 的发现一致 [@jimenez2024swebench]。
- **Collapsed Context 应显著劣于 Full Context**：说明充分的上下文对于硬件工程设计是必需的，局部信息不足以推断全局约束。
- 不同模型对上下文长度的敏感性不同（如 Gemini 的 200K 窗口可能缩小 Oracle vs Full 的差距）。

## 6.4 各任务类型分析

@tbl:task-type-results 按任务类型分解 pass@1。

| Harness + 模型 | instance-decl. | layout-design | connection-design | mating-design | comprehensive |
|---------------|---------------|---------------|-------------------|---------------|---------------|
| Kimi Code + k2.7 | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] |
| Codex + deepseek-v4-pro | [xx.x] | [xx.x] | [xx.x] | [xx.x] | [xx.x] |

Table: 各任务类型的 pass@1（Full Context）。{#tbl:task-type-results}

> **需填入数据**：完成按类型细分统计后替换。

初步预期：

- `instance-declaration`（声明 Part 实例）应是最简单的类型，因为主要涉及填写属性值，DTS 挑战集中在 L1（schema/类型）。
- `layout-design`（空间布局）应是最困难的类型之一，因为涉及 L3 的 U 位/间距和 L4 的碰撞检查。
- `comprehensive`（综合）应是最难的类型，因为需要同时操作 PDL/PML/PLL 三层并保持全局约束一致性。

## 6.5 成本分析

SD-HWE-Bench 的成本来自两个层面：(1) 模型推理的 token 消耗与 API 费用；(2) Harness 基础设施（DTS 检查、容器启动、交付物生成）的算力和时间。我们将二者分开报告。

### 6.5.1 模型推理成本

@tbl:model-cost 给出各模型每次 rollout 的平均 token 消耗与 API 费用。

| 模型 | 提供商 | Avg. Input Tokens | Avg. Output Tokens | Avg. API Cost ($) |
|------|--------|-------------------|---------------------|--------------------|
| kimi-code/k2.7 | Moonshot AI | [N] | [N] | [x.xx] |
| deepseek-v4-pro | DeepSeek | [N] | [N] | [x.xx] |

Table: 模型推理成本（per rollout，Full Context，不含 self-check 轮次）。{#tbl:model-cost}

### 6.5.2 Harness 执行时间

@tbl:harness-time 给出每次 rollout 的墙钟时间分解。

| Harness + 模型 | Agent 推理 (s) | DTS 检查 (s) | 容器开销 (s) | 总时间 (s) |
|---------------|----------------|-------------|-------------|-----------|
| Kimi Code + k2.7 | [xxx] | [xx] | [xx] | [xxx] |
| Codex + deepseek-v4-pro | [xxx] | [xx] | [xx] | [xxx] |

Table: Harness 执行时间分解（per rollout，Full Context，单次生成无 self-check）。{#tbl:harness-time}

> **需填入数据**：完成实验后统计 token 消耗、API 账单和墙钟时间。

成本分析对 benchmark 实用性的评估至关重要：如果评测成本过高，将限制社区参与和规模化实验。SD-HWE-Bench 的 DTS 分层设计倾向于低成本——L0–L2 毫秒级检查在 Agent 本地运行，容器化 L3–L5 检查也控制在秒级，使得大部分常见错误能被快速发现，减少对昂贵 LLM 推理的依赖。
