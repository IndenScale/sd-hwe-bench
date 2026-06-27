# 4. 数据集

本章详细描述 SD-HWE-Bench 的数据集构建过程。第 4.1 节给出整体 pipeline 的漏斗数字；第 4.2 节介绍 canonical 工程；第 4.3 节描述任务提取流程与质量控制；第 4.4 节给出数据集的统计特征。

## 4.0 设计规范驱动的任务构造

SD-HWE-Bench 的核心设计原则之一是**规范驱动性（Specification-Driven Design）**：Agent 必须主动查阅项目中的设计规范（而非依赖 prompt 中全部列出）才能完成设计。这是区分「指令遵循能力」和「工程设计能力」的关键机制。

具体实现方式（详见 AGENTS.md 和 docs/canonical-project-guidelines.md）：

- **Canonical project 规范**：每个 canonical project 的 docs/ 目录包含设计规范文档（如 rack-design-spec.md），定义字段名、目录结构、约束规则和设计流程。规范按专业拆分（电气、结构、消防等），支持多领域扩展。
- **任务提取时自动注入**：tools/extract_tasks.py 将 canonical project 的 docs/ 完整复制到每个 task 的 scaffold/ 和 solution/ 中。
- **Prompt 模式区分**：PromptBuilder 根据 Actor 类型区分输出模式——CLI Actor（Kimi/Codex/Gemini）收到的 prompt 指引其主动阅读规范文件；API Actor（OpenAI/DeepSeek）收到的 prompt 内联完整规范内容——确保两种模式下 Agent 都能访问设计标准。
- **任务 requirement 的工程设计语义**：task_manifest.yaml 中的 requirement 仅描述功能/性能目标（如「为机柜声明两路 PDU，每路容量 2000W」），不泄露具体字段名、公式或阈值——这些信息必须从规范中获取。

## 4.1 构建 Pipeline 概览

SD-HWE-Bench 的数据集构建遵循四阶段 pipeline（图 2）：

```text
Canonical 工程 Authoring        Commit 序列化
   3 个完整 ADL 工程      →    人工迭代，每个 commit 是有意义增量
                ↓
        任务提取 (extract_tools.py)
   相邻 commit → 自动生成任务（需求描述/上下文/gold patch/测试）
                ↓
        执行验证 + 人工审核
   gold patch 必须通过 piki check
   人工审核问题描述正确性和任务合理性
                ↓
        最终任务集
   46 个任务 × 3 个子领域
```

**Figure 2**：SD-HWE-Bench 数据集构建 pipeline。{#fig:pipeline}

最终数据集规模：

| 阶段 | 数量 |
|------|------|


### 4.1.1 v2 扩展（2026-06-27）

基于初版 34-task 实验的诊断分析（CLI Actor 饱和、L2 单层过载、easy 占比过高），v2 进行了以下扩展：

1. **5 个复合 easy 任务**（telecom-easy-compound-001~005）：递增依赖链设计——从设备声明→端口实例→光模块/光纤→配合约束→电源 IEC 配合，每个任务建立在前一个任务的解决方案之上。增加 easy 任务的依赖链深度（从 1-2 层到 3-4 层）。

2. **4 个涌现约束任务**（telecom-emergent-001~004）：约束不显式声明在 requirement 中，Agent 必须从 scaffold 已有实例中推断——命名规范、必填字段、物理尺寸兼容性、U 位间隔惯例。测试 Agent 的"模式发现"能力。

3. **3 个跨专业综合任务**（telecom-cross-001~003）：综合电气（功率预算、相位平衡）、结构（地板载荷、机柜承重）和消防（散热约束、维护通道）多域约束，模拟真实工程中跨专业协调的复杂性。

4. **L2 评分层拆分**：原 16 条 L2 规则拆分为 L2a（标识/外键, 5 条）、L2b（接口/端口, 7 条）、L2c（配合/目录, 4 条）三个子层，各 5% 权重，避免单字段错误导致的连锁扣分。

5. **难度重标定**：7 个原 easy 任务升级为 medium，总分布从 easy 50%→39%, medium 38%→46%, hard 12%→15%。

| Canonical 工程 | 3 个（telecom-rack / datacenter / telecom-site） |
| POC 手工任务 | 5 个 |
| 总任务数 | 46 个 |

## 4.2 Canonical 工程

SD-HWE-Bench 基于三个 canonical ADL 工程构建任务，覆盖不同的硬件工程子领域和设计复杂度。

### 4.2.1 电信机柜扩容工程（Telecom Rack Expansion）

**领域**：电信基础设施
**ADL 规模**：约 800–1200 行 PDL + 1500–2500 行 PML + 600–1000 行 PLL
**Part 类型**：15–25 种（交换机、服务器、PDU、PatchPanel、UPS、光纤盒、理线器等）
**设计约束**：功率预算、U 位分配、散热间隙、接口兼容性、承重限制、线缆路由

该工程模拟一个 42U 标准电信机柜从空白到满载的完整部署过程。初始 commit 仅包含机柜框架和基础 PDL 定义。14 个 commits 逐步增加：PDU 电源分配（C2-C3）、设备声明与 U 位分配（C4-C6）、连接设计（C7-C9）、光纤配合（C10-C14）。C15 扩展至跨机柜光纤连接——第二个机柜 RACK-A02 部署服务器并通过 5.0m OM4-LC-LC 光纤回连至 RACK-A01 交换机。工程附有完整设计规范文档（docs/rack-design-spec.md），涵盖 U 位编号规则、PDU 字段规范、设备声明规范和设计流程——这些规范在任务提取时自动注入到每个 task 的 scaffold 中，Agent 必须查阅规范才能完成设计。

共提取 15 个任务（telecom-rack-001 ~ 015），其中 rack-015 为跨机柜综合任务（hard）。

### 4.2.2 数据中心机房工程（Datacenter Deployment）

**领域**：电信/数据中心基础设施
**ADL 规模**：约 500–800 行 PDL + 1000–1500 行 PML + 400–600 行 PLL
**Part 类型**：10–15 种（机房、机柜排、机柜、PDU、列间空调、ToR 交换机、服务器、抬高地板、物流坡道等）
**设计约束**：平面布局、维护通道宽度、机柜承重、抬高地板载荷、门开合扫掠区、车辆路径可达性

该工程模拟一个数据中心机房从空白到完整部署的过程。8 个 commits 逐步增加：机房与机柜排声明（C1-C3）、机柜装配与设备部署（C4-C5）、ToR 组网与电源（C6-C7）、配合与交付物生成（C8）。附有设计规范文档（docs/dc-design-spec.md）。

共提取 8 个任务（datacenter-001 ~ 008）。

### 4.2.3 户外基站站点工程（Telecom Site）

**领域**：电信/户外基础设施
**ADL 规模**：约 300–500 行 PDL + 600–1000 行 PML + 200–400 行 PLL
**Part 类型**：8–12 种（户外机柜、天线、RRU、BBU、馈线、防雷接地、DC 电源等）
**设计约束**：IP 防护等级、防雷接地、馈线路由、DC 电源分配、must-clear 安全间距

该工程模拟户外基站从单机柜到完整站点的部署过程。6 个 commits 逐步增加：户外机柜声明（C1-C2）、天线与 RRU 部署（C3）、BBU 与馈线连接（C4）、防雷接地系统（C5）、电源与配合生成（C6）。附有设计规范文档（docs/site-design-spec.md）。

共提取 6 个任务（telecom-site-001 ~ 006）。

### 4.2.4 任务与 Commit 的对齐

每个 canonical 工程的设计原则：

1. **每个 commit 是一个有意义的设计增量**：不是一个文件的一行修改，而是一个完整的设计决策（如"增加一个交换机并更新功率预算"）。
2. **每个 commit 通过 piki check**：确保任何时候 checkout 到的状态都是合法的 ADL 工程。
3. **Commit message 可作为任务描述的基础**：清晰的 commit message 在人工审核后转化为任务需求自然语言。

## 4.3 任务提取流程

`tools/extract_tasks.py` 是自动任务提取工具。其核心算法：

1. 遍历 canonical 工程的 git log，识别相邻 commit 对 `(commit_k, commit_{k+1})`。
2. 对于每对 commit：
   - **生成需求描述**：读取 commit message + `git diff` 的变更摘要，结合领域模板生成自然语言任务需求。
   - **生成 scaffold**：checkout `commit_k` 的完整工程状态，作为任务上下文。
   - **提取 gold patch**：计算 `git diff commit_k commit_{k+1}` 中影响 ADL 文件（`.yaml` 在 `models/` 下）的变更。
   - **提取 DTS 测试**：在 `commit_{k+1}` 状态运行 `piki check`，记录所有通过的 DTS 层和规则。
   - **判断任务类型**：根据变更涉及的 ADL 层（PDL/PML/PLL）和变更性质（新建/修改/删除），自动分类为 `instance-declaration` / `layout-design` / `connection-design` / `mating-design` / `comprehensive`。

3. 输出每个候选任务的 `task.yaml` 骨架和 `scaffold/`、`solution/` 目录。

### 4.3.1 质量控制

所有自动提取的任务随后进入人工审核：

- **需求准确性**：检查自动生成的任务需求是否准确反映 commit 的变更意图。
- **Scaffold 完整性**：确认 scaffold/ 包含任务所需的全部上下文文件。
- **Solution 正确性**：验证 solution/ 中的 gold patch 确实满足任务需求，且 `piki check` 全通过。
- **难度标注**：根据修改范围、跨域耦合和 DTS 覆盖层数手动标注 difficulty。
- **Rubrics 补充**：为需要定性评估的任务（如 comprehensive 类型）补充 rubrics。

不符合标准的任务被直接剔除，不进入最终数据集。所有 34 个 reference solution 均通过 `pytest tests/test_reference_solutions.py` 全量回归验证（46/46 pass）。

## 4.4 数据集统计特征

@tbl:dataset-stats 给出了数据集的统计特征。

| 统计维度 | 值 |
|---------|-----|
| 总任务数 | 46 |
| 领域数 | 1（telecom），含 3 个子领域（rack / datacenter / site） |
| Canonical 工程数 | 3（telecom-rack / datacenter / telecom-site） |
| POC 手工任务 | 5 个 |
| 任务类型分布 | instance-declaration: 21, mating-design: 11, connection-design: 6, layout-design: 3, comprehensive: 5 |
| 难度分布 | easy: 18, medium: 21, hard: 7 |
| 平均 scaffold ADL 行数 | ~800 行 |
| 平均 gold patch 行数 | ~30 行 |
| 平均 gold patch 涉及文件数 | ~2.5 个 |
| 平均 DTS 覆盖规则数 | 30 条/任务（涵盖 L1 schema 校验、L2 引用完整性、L3 工程约束、L4 几何碰撞） |
| 任务需求平均长度 | ~80 词（增量任务），~250 词（综合任务） |

Table: SD-HWE-Bench 数据集统计。{#tbl:dataset-stats}

### 4.4.1 任务特性总结

SD-HWE-Bench 的任务具有以下核心特性：

1. **真实硬件工程设计任务**：任务来自 canonical ADL 工程的真实 commit 历史，每个 commit 对应一个有意义的完整设计增量，而非人工合成的 toy problem。
2. **多物理域耦合**：单个任务可同时涉及电气连接（电源线/信号线）、物理配合（螺栓/卡扣）、空间布局（U 位/间距/散热）、热管理和结构约束。
3. **长上下文**：scaffold 通常包含 800–3000+ 行 ADL 声明、数十个 Part 实例、多层装配关系——要求 Agent 具备长上下文理解和全局一致性保持能力。
4. **可执行数字模型**：每个任务绑定 DTS 分层断言（平均 30 条规则/任务），可在毫秒至秒级给出确定性正确/错误信号。
5. **跨抽象层编辑**：修改可能发生在 Part 类型定义（PDL）、实例声明、连接关系（PML）、布局位置（PLL）任意一层——要求 Agent 理解三层正交的语言语义。
6. **可持续更新**：canonical 工程的任何新增 commit 都可自动提取为新任务，无需重新构建数据集。

## 4.5 数据集划分

数据集按 canonical 工程来源划分训练/验证/测试集：

- **训练集**：部分 canonical 工程的连续 commit 段，用于模型微调和 prompt 调优。
- **验证集**：保留的 commit 段，用于方法开发和超参数选择。
- **测试集**：完整保留的 canonical 工程（全部 commit），用于最终评测和 leaderboard。

测试集 canonical 工程的选择原则：不与训练/验证集共享任何 Part 类型定义或工程场景，以确保评测的独立性和泛化性。

## 4.6 与 Related Benchmarks 的数据集对比

@tbl:dataset-comparison 将 SD-HWE-Bench 的数据集与代表性 benchmark 对比。

| 维度 | SWE-bench | SWE-bench M | HumanEval | SD-HWE-Bench |
|------|-----------|-------------|-----------|-------------|
| 任务来源 | 开源 GitHub repo | 开源 GitHub repo | 手写 | Canonical ADL 工程 |
| 领域 | Python 代码 | JS/TS + 视觉 | 算法/逻辑 | 物理工程设计 |
| 上下文规模 | 数百-数万行 | 数百-数万行 | 数行函数签名 | 800-3000+ 行 ADL |
| 反馈类型 | pytest 通过/失败 | pytest + 视觉 | 输入/输出对 | DTS L0-L4 分层（30 规则/任务） |
| 多域耦合 | 无 | 有限 | 无 | 电气/热/结构/信号 |
| 几何约束 | 无 | 有限 | 无 | 碰撞/U位/间距 |
| 新任务扩展 | 依赖新 issue | 依赖新 issue | 手写新题 | 自动从 commit 提取 |

Table: 数据集构建范式对比。{#tbl:dataset-comparison}
