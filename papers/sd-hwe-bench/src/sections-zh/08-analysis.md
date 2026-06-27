# 8. 错误模式与难度分析

本章对 Agent 失败进行深入诊断——不只报告数字，而是分析**为什么失败、瓶颈在哪里、难度因子是什么**。这是让 SD-HWE-Bench 从"排行榜工具"升格为"科学分析平台"的关键章节。

## 8.1 核心发现：Actor Gap

我们的实验揭示了一个此前未被充分讨论的现象——**同一模型在不同 Agent 框架下的表现存在系统性差异**（Actor Gap）：

| 模型 | CLI Native | API Proxy | Δ |
|------|-----------|----------|---|
| DeepSeek-v4-Flash | 100% (15/15) | 80% (16/20) | +20pp |
| DeepSeek-v4-Pro | 100% (15/15) | 90% (18/20) | +10pp |

Table: Actor Gap——同一模型在 CLI vs API 框架下的 pass@1 差异。{#tbl:actor-gap}

### 8.1.1 根因分析

**文件系统交互能力**。CLI Actor（kimi-code / codex exec）在真实文件系统中操作——可以 `ls` 查看目录结构、`cat` 阅读规范文档、在正确的路径创建文件。API Actor 依赖 prompt 中内联的规范文本和从代码块解析 YAML——这带来了两个信息损耗环节：

1. **规范查阅损耗**：内联在 prompt 中的规范文本随上下文增长而被"稀释"，Agent 在生成长 YAML 时容易遗忘前面的字段名约定（如 `capacity_w` vs `power_capacity_w`）。
2. **YAML 解析损耗**：从模型响应中解析 YAML 代码块时，如果模型使用了非标准格式（缩进不一致、路径注释缺失），解析器可能丢失文件路径信息。

**自检循环未触发**。两种 Actor 模式下 self-check 平均轮次均 < 0.5——说明当前 pass@1 实验中，自动修复机制未充分参与。这意味着 reported pass@1 更接近「单次生成」而非「多轮修复后」的表现。CLI Actor 虽然 workflow 中有 `piki check` 建议，但在 pass@1 设置下 Agent 通常不主动执行自检。

**设计规范驱动的挑战**。规范驱动性（Specification-Driven Design）是 SD-HWE-Bench 的核心设计原则——任务 requirement 仅描述功能目标，具体字段名、公式和阈值必须从规范文档中获取。CLI Actor 可以像人类工程师那样"翻阅规范文档"，而 API Actor 只能依赖一次性注入的规范文本。

### 8.1.2 方法论意义

Actor Gap 的发现对 benchmark 设计有重要启示：

1. **Benchmark 评测的是 Agent 系统，不只是模型**。Agent 框架的工程质量（文件系统访问、命令行工具集成、自检循环）对结果有决定性影响。
2. **实验结果必须明确报告 Actor 配置**。不同实验室使用不同的 Agent 框架（CLI native / API proxy / LangChain / custom harness），不可直接比较 pass@1 数字。
3. **Benchmark 的区分度体现在跨框架差异上**。一个 benchmark 如果在所有框架下都 100%，说明任务太简单；如果只在某个框架下 100%，说明 benchmark 真实反映了 Agent 系统的能力差距。

## 8.2 失败模式分类

我们将 Agent 的失败按根因分为四类（基于 API 路径数据，因 CLI 路径无失败）：

### 8.2.1 语法/格式错误（L0 失败）

Agent 输出的 YAML 无法解析，或完全未生成 `expected_files`。

**出现频率**：极低（0/54 runs）。piki YAML schema 简单，Agent 极少产出不可解析的 YAML。

### 8.2.2 类型/约束违背（L1/L2 失败）

Agent 的语义不合理——属性值非法、引用不存在的 Part，或端口名不存在。

**典型表现**：

- `interface_type: 'SFP28'`（schema 要求 `SFP28-module` 或 `SFP28-cage`）
- 引用了一个未在 PDL 中定义的 `part_id`
- 连接端点 `from_port` 未定义

**根因**：Agent 未严格参照 schema 和 PDL 中的已定义 Part 列表。API 路径下规范内联到 prompt 后，Agent 在生成长输出时容易遗忘字段精确值。

**出现频率**：API Flash 20%、API Pro 15%（L1+L2 合计）。

### 8.2.3 设计逻辑遗漏（L3 失败）

Agent 的方案在语法和语义上都合法，但**遗漏了某条设计规则**——功率预算超限、U 位冲突、接口不兼容。

**典型表现**：

- PDU 功率预算超限（TELECOM-POWER-001）
- 连接端口类型不兼容（TELECOM-CONN-002）：如光纤连接器配对错误

**根因**：Agent 在长上下文、多约束空间中无法保持全局一致性——它"知道"所有规则，但无法在设计过程中**同时**满足它们。

**出现频率**：API Flash 20%、API Pro 10%。

### 8.2.4 几何/空间推理（L4 失败）

**出现频率**：0/54 runs。当前 task 集中 L4 规则主要为维护空间、地板载荷等静力学检查，Agent 在设计过程中通常能通过。

## 8.3 各模型失败模式特征

@tbl:failure-dist 给出 API 路径各模型的失败模式分布。

| Agent | L1 (Schema) | L2 (引用) | L3 (约束) | L4 (几何) |
|-------|------------|----------|----------|----------|
| API DS-v4-Flash | 1 (5%) | 3 (15%) | 4 (20%) | 0 |
| API DS-v4-Pro | 1 (5%) | 2 (10%) | 2 (10%) | 0 |
| CLI (all) | 0 | 0 | 0 | 0 |

Table: 各模型的失败模式分布（首次生成，Full Context，pass@1）。CLI 路径 35 个 task-runs 无任何失败。{#tbl:failure-dist}

## 8.4 难度因子分析

### 8.4.1 规范驱动性

SD-HWE-Bench 最具区分度的设计是规范驱动性——Agent 必须**主动查阅**设计规范文档才能完成设计。这在 easy 任务上不构成障碍（字段少、参照简单），但在 hard 任务上（如 telecom-rack-015 的跨机柜光纤，需要同时遵循 U 位规则、PDU 字段规范、端口/光模块/光纤/连接/配合 5 类规范）成为核心瓶颈。

API 路径在 hard 任务上的低通过率（Flash 25%、Pro 50%）印证了这一点——一次性注入的规范文本在长上下文生成中被稀释。

### 8.4.2 跨文件协调

hard 任务平均涉及 15+ expected_files，Agent 需要在多个 YAML 文件之间保持引用一致性（如端口实例 → 光模块实例 → 光纤实例 → 配合实例的引用链）。CLI Actor 可以通过文件系统逐个验证，API Actor 只能在单次生成中"记住"所有引用关系——这是 CLI 100% vs API 25-50% 在 hard 上的根本原因。

### 8.4.3 Easy 任务占比

当前 34 个任务中 easy 占 50%（17/34）。这些任务主要测试 Agent 是否理解规范文档中的字段名和目录结构，不涉及复杂的跨文件协调。这是数据集当前的主要局限——**too many easy tasks, not enough hard discriminative tasks**。

改进方向（不在本文范围内）：增加跨专业综合任务（如同时涉及电气+结构+消防）、引入 hidden constraint 设计（规范文档中分散在多处的隐含约束条件）、增加 failure injection 任务（在 scaffold 中埋入错误让 Agent 检测和修复）。

## 8.5 Top 失败规则（API 路径）

@tbl:top-failures 列出了 API 路径上最常见的 DTS 规则失败。

| 规则 ID | 名称 | 失败次数 | 类型 |
|---------|------|---------|------|
| TELECOM-CONN-001 | 连接端点存在性检查 | 3 | L2 引用 |
| TELECOM-FK-001 | 外键完整性检查 | 2 | L2 引用 |
| TELECOM-POWER-001 | PDU 功率预算检查 | 2 | L3 约束 |
| TELECOM-CONN-002 | 连接端口类型兼容性 | 2 | L3 约束 |

Table: API 路径 Top 失败规则。CLI 路径无失败。{#tbl:top-failures}

### 8.5.1 规则密度分析

每个任务底层平均执行 30 条确定性规则（9 个 L4 几何规则 + 10 个 L3 工程约束 + 6 个 L2 引用规则 + 5 个 L1 schema 规则）。对比 SWE-bench 每个 task 通常只有 1-3 个 pytest 测试用例——SD-HWE-Bench 的约束密度实际上更高，但当前规则集中在预防性检查（catch errors），缺少压力测试级别的高难度约束。

未来可通过引入更激进的约束（如 multi-rack 全局功率优化、cross-domain 消防通道与机柜布局的 joint constraint）提升规则的有效区分度。
