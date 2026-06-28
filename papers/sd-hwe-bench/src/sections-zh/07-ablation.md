# 7. 消融实验：DTS 反馈是否提升生成质量

SD-HWE-Bench 的核心假设之一是：确定性反馈（DTS）能够显著提升 Agent 在硬件工程设计任务上的通过率。本章通过 self-check hook 消融实验验证这一假设——对比 Agent 提交后自动运行 `piki check` 并迭代修复（self-check on）与不运行（self-check off）两种模式的通过率差异。

## 7.1 实验设计

**当前状态说明**：no-repair 实验中的 self-check engagement 极低（平均 < 0.5 轮），说明自动修复机制未有效参与——reported pass@1 更接近「单次生成」表现。这既是当前数据的局限性（repair 效果的信号被噪声淹没），也为消融实验设计提供了具体参数的基准：修复循环必须主动触发（非通过 self-check 钩子等待 Agent 自行调用 piki check），且需设置合理的迭代轮次上限（建议 R=3-5）。

我们设计对比两组实验：

- **No-Repair**：Agent 单次生成，不获得 DTS 反馈。若首次生成失败，任务直接判为 unresolved。
- **Repair**：Agent 在首次生成失败后，获得完整 DTS 错误报告（含具体层、规则 ID、失败位置、自然语言描述），被要求修复失败项。最多迭代 R=5 轮，或直到 DTS 全部通过。

**关键控制变量**：

- 选用当前 pass@1 水平较低的模型或在其失败的任务子集上运行，使 improvement 空间最大。
- 选用最能代表 DTS 价值的任务子集：主要包含 L2（引用完整性）和 L3（ASA）失败案例——这类错误由设计逻辑缺失（如忘了写功率预算验证、引用了不存在的 Part）而非语法/类型错误造成，最可能通过多轮迭代修复。
- 每任务独立执行 3 次 pass，减少统计噪声。

## 7.2 结果

@tbl:ablation-results 给出 self-check off vs on 的通过率对比。

| Agent | pass@1 (no-repair) | pass@1 (repair) | Δ | Avg. Repair Rounds |
|-------|-------------------|-----------------|---|--------------------|
| Kimi (k2.7) | 84.7% | [待跑] | [待跑] | 0 [1] |
| DeepSeek-v4-Pro | 86.7% | [待跑] | [待跑] | 0 [1] |

Table: Self-check off vs on pass@1 对比。{#tbl:ablation-results}

> [1] 当前 pass@1 实验使用 --self-check 钩子（非 run-repair 命令），self-check engagement < 0.5 轮——Agent 几乎不会主动调用 piki check。需使用独立的 run-repair 命令重新实验。
>
> **注**：两组模型在 30 任务上均未饱和（Kimi 84.7%、DeepSeek-v4-Pro 86.7%），repair 实验有 10–15pp 的潜在改善空间。

预期结果：

- Repair 应带来显著的 pass@1 提升（预期 +10–30pp）。
- DeepSeek-v4-Pro 可能从 repair 中获益更大——初步观察显示其生成质量波动较大，但具有较强的指令遵循能力，因此 DTS 错误报告可能对其特别有效。
- 平均 repair 轮数应在 2–3 轮——大部分可修复错误在 2 轮内解决，少数顽固错误（如跨层耦合冲突）可能需要 4–5 轮。

## 7.3 逐层分解

@tbl:ablation-layer 按 DTS 层分解 self-check off 和 on 的通过率，揭示 DTS 反馈在不同检查层上的效果差异。

| DTS 层 | no-repair pass (DeepSeek) | repair pass | Δ (预期) |
|-----------|--------------------------|-------------|----------|
| L0 (语法/交付物) | ~100% | ~100% | 0pp |
| L1 (语义) | ~95% | ~95% | 0pp |
| L2 (引用完整性) | ~85% | ~92% | +5-10pp |
| L3 (ASA 静态分析) | ~80% | ~90% | +10-15pp |
| L4 (ADA 动态仿真) | 任务相关 | 任务相关 | +0-10pp |
| L5 (几何干涉) | ~95% | ~95% | 0pp |

Table: 各 DTS 层的 self-check off vs on 通过率。{#tbl:ablation-layer}

> **注**：L2+L3 的预期改善基于 DeepSeek 的失败模式分布（L2 引用错误、L3 约束违规占失败 majority）——这类错误具有最高的可修复性（Agent 接收到明确的「缺失引用 X」「约束 Y 在位置 Z 被违反」后可针对性修正）。L0/L1/L5 基本接近天花板，修复空间极小。

**预期观察**：

- **L3（ASA 静态分析）应获益最大**：ASA 的失败通常是"忘了某条规则"而非"不知道规则内容"。DTS 诊断明确指出遗漏的规则后，Agent 有能力补充修正。这体现了确定性反馈的核心价值——将"设计遗漏"转化为"可修复错误"。
- **L0/L1/L5 几乎不会从 self-check 中获益**：语法、schema 和几何错误通常是 Agent 基本能力问题，而非可迭代修复的设计缺失。
- **L2（引用完整性）中等获益**：引用错误有时是 Agent 全局疏忽（如前文定义了一个 Part，后文引用时写错了 ID），DTS 反馈可以直接指出缺失的引用。
- **L4（ADA）仅在 AIDC 任务有样本**：仿真硬约束失败可能较难通过多轮修复完全解决，因为涉及全局参数耦合。

## 7.4 典型案例分析

> 本节应在实验完成后补充 1–3 个 before/after 案例。

### 案例 1（占位符）

**任务**：`telecom/comprehensive-001`
**失败模式（self-check off）**：L3 功率预算检查失败——Agent 增加了第 4 台交换机但忘记更新 PDU 容量声明。
**修复过程（repair）**：DTS 报告指出 `power_budget: exceeded by 175W at rack total`。第 2 轮 Agent 检查了 PDL 中的 PDU 定义，发现型号选的是 3kW 而非 5kW，将 PDU 升级为 5kW 型号后通过。

**启示**：这不是"不会设计"，而是"设计过程中遗漏了约束传播"——DTS 填补了这一遗漏。

### 案例 2（占位符）

**任务**：`telecom/layout-design-001`
**失败模式（self-check off）**：L3 U 位冲突——Agent 将两台设备分配到 U25-U26 和 U26-U27，产生了 U26 重叠。
**修复过程（repair）**：DTS 报告明确标出 `U-position conflict at U26 between switch-3 and server-2`。第 2 轮 Agent 将 server-2 移到 U27-U28 后通过。

**启示**：U 位计算本身不复杂，但在多设备布局中容易出错。确定性反馈将"手动验算"自动化，Agent 只需修正位置即可。

### 案例 3（占位符）

**任务**：`telecom/connection-design-001`
**失败模式（self-check off）**：L2 引用完整性——Agent 声明了 `source_port: eth1/1/25` 但该交换机实际只有 24 个端口。
**修复过程（repair）**：DTS 报告给出了端口列表和计数。Agent 修正为 `eth1/1/24`（改为使用实际存在的端口）。

**启示**：这类错误来自 Agent 对设计细节的"幻觉"——确定性反馈是消除这种幻觉的最直接手段。

## 7.5 讨论：DTS 反馈的因果价值

消融实验试图回答一个深层问题：**工程设计的确定性反馈是否能因果性提升 Agent 的生成质量？**

如果 repair 带来了显著提升，这意味着：

1. Agent 的瓶颈不在于"缺乏设计知识"，而在于"无法在长上下文、多约束空间中稳定应用这些知识"——与开放域知识问答的失败模式不同。
2. 提供**廉价、高频、确定性**的反馈信号（DTS），而非昂贵、低频、概率性的信号（高精度仿真或人工审查），是提升工程 Agent 能力的有效路径。
3. SD-HWE-Bench 作为 RLVR benchmark 的价值得到验证：确定性奖励 + repair loop = 可训练的性能提升路径。

如果 repair 提升有限（<5pp），则说明当前 LLM Agent 的能力上限不在于反馈不足，而在于 ADL 语法/语义理解本身的缺陷——需要 ADL-specific 预训练或模型能力提升才能突破。

无论哪种结果，消融实验都为 SD-HWE-Bench 的 benchmark 价值提供了证据：它不仅能评估"谁更强"，还能诊断"为什么差"和"怎么提升"。
