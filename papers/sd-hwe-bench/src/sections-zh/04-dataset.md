# 4. 数据集

本章详细描述 SD-HWE-Bench 的数据集构建过程。第 4.1 节给出整体 pipeline 的漏斗数字；第 4.2 节介绍 canonical 工程；第 4.3 节描述任务提取流程与质量控制；第 4.4 节给出数据集的统计特征。

## 4.0 设计规范驱动的任务构造

SD-HWE-Bench 的核心设计原则之一是**规范驱动性（Specification-Driven Design）**：Agent 必须主动查阅项目中的设计规范（而非依赖 prompt 中全部列出）才能完成设计。这是区分「指令遵循能力」和「工程设计能力」的关键机制。

具体实现方式（详见 AGENTS.md 和 docs/guides/canonical-project-design.md）：

- **Canonical project 规范**：每个 canonical project 的 docs/ 目录包含设计规范文档（如 rack-design-spec.md），定义字段名、目录结构、约束规则和设计流程。规范按专业拆分（电气、结构、消防等），支持多领域扩展。
- **任务提取时自动注入**：tools/extract_tasks.py 将 canonical project 的 docs/ 完整复制到每个 task 的 scaffold/ 和 solution/ 中。
- **Prompt 设计**：PromptBuilder 生成的 prompt 指引 Agent 主动阅读规范文件，requirement 仅描述功能目标、具体字段名和公式必须从 `docs/` 自行获取。
- **任务 requirement 的工程设计语义**：task_manifest.yaml 中的 requirement 仅描述功能/性能目标（如「为机柜声明两路 PDU，每路容量 2000W」），不泄露具体字段名、公式或阈值——这些信息必须从规范中获取。

## 4.1 构建 Pipeline 概览

SD-HWE-Bench 的数据集构建遵循四阶段 pipeline（图 2）：

```text
Canonical 工程 Authoring        Commit 序列化
   5 个完整 ADL 工程      →    人工迭代，每个 commit 是有意义增量
                ↓
        任务提取 (extract_tools.py)
   相邻 commit → 自动生成任务（需求描述/上下文/gold patch/测试）
                ↓
        执行验证 + 人工审核
   gold patch 必须通过 piki check
   人工审核问题描述正确性和任务合理性
                ↓
        最终任务集
   37 个任务 × 1 个领域
```

**Figure 2**：SD-HWE-Bench 数据集构建 pipeline。{#fig:pipeline}

最终数据集规模：

| 阶段 | 数量 |
|------|------|
| Canonical 工程 | 6 个（telecom-rack / datacenter / telecom-site / datacenter-hall / datacenter-hall-60mw / aidc-detailed） |
| 阶段式 commit 任务 | 16 个（4 rack + 5 datacenter + 7 telecom-site） |
| POC 手工任务 | 5 个 |
| 复合 easy 任务 | 5 个 |
| 涌现约束任务 | 4 个 |
| 跨专业综合任务 | 3 个 |
| AIDC 任务 | 4 个 |
| **总任务数** | **37 个** |

### 4.1.1 v2 扩展（2026-06-27）

基于初版 34-task 实验的诊断分析（CLI Actor 饱和、L2 单层过载、easy 占比过高），v2 进行了以下扩展：

1. **5 个复合 easy 任务**（telecom-easy-compound-001~005）：递增依赖链设计——从设备声明→端口实例→光模块/光纤→配合约束→电源 IEC 配合，每个任务建立在前一个任务的解决方案之上。增加 easy 任务的依赖链深度（从 1-2 层到 3-4 层）。

2. **4 个涌现约束任务**（telecom-emergent-001~004）：约束不显式声明在 requirement 中，Agent 必须从 scaffold 已有实例中推断——命名规范、必填字段、物理尺寸兼容性、U 位间隔惯例。测试 Agent 的"模式发现"能力。

3. **3 个跨专业综合任务**（telecom-cross-001~003）：综合电气（功率预算、相位平衡）、结构（地板载荷、机柜承重）和消防（散热约束、维护通道）多域约束，模拟真实工程中跨专业协调的复杂性。

4. **难度重标定**：部分原 easy 任务升级为 medium/hard，总分布从 easy 50%→19%, medium 38%→38%, hard 12%→43%。

### 4.1.2 v7 扩展（2026-06-29）

针对 AIDC 任务重叠度过高、缺乏施工/可建性维度的问题，v7 对 AIDC 任务进行了体系化重构：

1. **退役原 4 个 AIDC 任务**：`aidc-operation-001/002`、`aidc-co-design-001/002` 移至 `tasks/telecom/_legacy/`，不再计入数据集。

2. **新增 4 个 AIDC/数据中心任务**，覆盖从 edge 到 60MW、从概念设计到施工建造的全生命周期：
   - `edge-dc-design-001`（medium）：14.8kW 边缘数据中心设计-调度联合优化（`canonical/datacenter-hall`）。
   - `aidc-conceptual-design-001`（hard）：60MW AIDC 概念设计-调度联合优化（`canonical/datacenter-hall-60mw`）。
   - `aidc-detailed-design-001`（hard）：60MW AIDC 详细设计（`canonical/aidc-detailed`），包含吊装方案、临时道路、VDC 工作面等施工可建性检查。
   - `aidc-epc-001`（hard）：60MW AIDC EPC 施工排程与风险响应（`canonical/aidc-detailed`），使用 CPML 施工排程模型。

3. **施工可建性 Critic**：`ConstructabilityCritic` 对详细设计任务检查重型设备吊装方案（起重机吨位、作业半径、净空、吊点）、主吊车租赁窗口、VDC 工作面配置。

4. **CPML/EPC 施工排程引擎**：`src/sd_hwe_bench/construction/` 提供活动网络、资源约束、天气/供应链延迟、应急预案的离散事件调度；`EPCCritic` 执行工期、资源、应急预案硬约束与 20 场景 SLA 鲁棒性评估。

5. **详细设计 canonical 工程**：`canonical/aidc-detailed/` 在 60MW 物理模型基础上增加建筑 geometry、架空地板、车辆通道、大门、机柜行列布局与 `placed-on` 配合，通过 `piki check`。

### 4.1.3 v6 评分层统一与 v7 扩展

为避免文档、代码与论文中对评分层的矛盾表述，v6 对 DTS 分层进行了统一：

- **L0–L5 为确定性 QA 层**，L6 预留为 FEM/CFD 等高精度物理仿真（本次未启用）。
- 原 L2a/L2b/L2c 合并回单一 **L2（引用完整性）**，不再细分子层。
- AIDC 任务中的仿真硬约束（温度、PUE、SLA 等）归入 **L4（ADA）**。
- 相对 baseline/reference 的优化分数不再占用层号，而是作为 **Performance Score（诊断指标）**。
- 交付物缺失视为生成失败，并入 **L0** 检查；`piki generate` 仍作为独立 DeliverableCritic 执行，但不单独设层。

v7 进一步扩展了 L4/L5 语义：

- **L4 按任务类型分支**：AIDC 设计任务走 `PerformanceCritic`，EPC 任务走 `EPCCritic`。
- **L5 合并几何与可建性**：piki 几何规则 + `ConstructabilityCritic`（吊装、主吊车租赁、VDC 工作面）。

## 4.2 Canonical 工程

SD-HWE-Bench 基于六个 canonical ADL 工程构建任务，覆盖不同的硬件工程子领域和设计复杂度。

### 4.2.1 电信机柜扩容工程（Telecom Rack Expansion）

**领域**：电信基础设施
**ADL 规模**：约 800–1200 行 PDL + 1500–2500 行 PML + 600–1000 行 PLL
**Part 类型**：15–25 种（交换机、服务器、PDU、PatchPanel、UPS、光纤盒、理线器等）
**设计约束**：功率预算、U 位分配、散热间隙、接口兼容性、承重限制、线缆路由

该工程模拟一个 42U 标准电信机柜从空白到满载的完整部署过程。4 个阶段 commit 逐步增加：机柜与 PDU 声明、设备部署、连接与光模块配合、电源配合与跨机柜扩容。工程附有完整设计规范文档（docs/rack-design-spec.md），涵盖 U 位编号规则、PDU 字段规范、设备声明规范和设计流程——这些规范在任务提取时自动注入到每个 task 的 scaffold 中，Agent 必须查阅规范才能完成设计。

共提取 4 个阶段任务（rack-stage1~4）。

### 4.2.2 数据中心机房工程（Datacenter Deployment）

**领域**：电信/数据中心基础设施
**ADL 规模**：约 500–800 行 PDL + 1000–1500 行 PML + 400–600 行 PLL
**Part 类型**：10–15 种（机房、机柜排、机柜、PDU、列间空调、ToR 交换机、服务器、抬高地板、物流坡道等）
**设计约束**：平面布局、维护通道宽度、机柜承重、抬高地板载荷、门开合扫掠区、车辆路径可达性

该工程模拟一个数据中心机房从空白到完整部署的过程。5 个阶段 commit 逐步增加：机房与机柜排声明、机柜入排配合、设备部署、散热空调声明与布线、Spine-Leaf 组网全互联。附有设计规范文档（docs/dc-design-spec.md）。

共提取 5 个阶段任务（dc-stage1~5）。

### 4.2.3 户外基站站点工程（Telecom Site）

**领域**：电信/户外基础设施
**ADL 规模**：约 300–500 行 PDL + 600–1000 行 PML + 200–400 行 PLL
**Part 类型**：8–12 种（户外机柜、天线、RRU、BBU、馈线、防雷接地、DC 电源等）
**设计约束**：IP 防护等级、防雷接地、馈线路由、DC 电源分配、must-clear 安全间距

该工程模拟户外基站从单机柜到完整站点的部署过程。7 个阶段 commit 逐步增加：塔桅与防雷、馈线声明与射频连接、接地与综合、射频参数与扇区规划、风载荷校核、散热冗余与热节流、邻频干扰协调。附有设计规范文档（docs/site-design-spec.md）。

共提取 7 个阶段任务（site-stage1~7）。

### 4.2.4 AIDC 主机房工程（Datacenter Hall）

**领域**：AI 数据中心从概念设计到施工建造的全生命周期
**ADL 规模**：约 600–1200 行 YAML（房间模型、设备模型、冷却/电力实例）+ 详细设计工程额外包含 geometry、layout、mating
**Part 类型**：8–12 种（机房、机柜、AI 服务器、冷水机组、变压器、储能、光伏等）
**设计约束**：PUE、碳排放、水消耗、电费、全生命周期成本（TCO）、温度约束、吊装可达性、施工工期与资源

该工程提供三个尺度的 AIDC 模型：

- **`canonical/datacenter-hall`**：14.8kW 小机房，8 台机柜，用于入门级设计-调度联合优化任务（`edge-dc-design-001`）。
- **`canonical/datacenter-hall-60mw`**：60MW 大型 AI 数据中心，200 台机柜、1000 台 60kW 液冷 AI 服务器，用于高区分度的概念设计-调度联合优化任务（`aidc-conceptual-design-001`）。
- **`canonical/aidc-detailed`**：在 60MW 模型基础上增加建筑 geometry、架空地板、车辆通道、大门、机柜行列布局与 `placed-on` 配合，用于详细设计任务（`aidc-detailed-design-001`）与 EPC 施工排程任务（`aidc-epc-001`）。

60MW 模型包含：8×10MW 离心式冷水机组（可缩放）、20MWh 储能、5MWp 光伏、双路 40MVA 变压器、分时电价、湿球温度曲线、变压器效率曲线。仿真引擎基于 RC 热网络计算每小时 PUE、碳排、水耗、电费，并支持全生命周期成本（CAPEX/OPEX/NPV/TCO/LCOE）评估。详细设计工程额外支持 piki 几何规则与 ConstructabilityCritic 吊装/VDC 检查。

共 4 个 AIDC 任务：`edge-dc-design-001`、`aidc-conceptual-design-001`、`aidc-detailed-design-001`、`aidc-epc-001`。

## 4.2.5 任务与 Commit 的对齐

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

不符合标准的任务被直接剔除，不进入最终数据集。所有 reference solution 均通过 `pytest tests/test_reference_solutions.py` 全量回归验证。

## 4.4 数据集统计特征

@tbl:dataset-stats 给出了数据集的统计特征。

| 统计维度 | 值 |
|---------|-----|
| 总任务数 | 37 |
| 领域数 | 1（telecom），含 3 个传统子领域（rack / datacenter / site）+ AIDC |
| Canonical 工程数 | 6（telecom-rack / datacenter / telecom-site / datacenter-hall / datacenter-hall-60mw / aidc-detailed） |
| POC 手工任务 | 5 个 |
| 复合 easy 任务 | 5 个 |
| 涌现约束任务 | 4 个 |
| 跨专业综合任务 | 3 个 |
| AIDC 任务 | 4 个 |
| 任务类型分布 | comprehensive: 24, instance-declaration: 5, layout-design: 2, connection-design: 2, mating-design: 2, co-design: 2, detailed-design: 1, epc: 1 |
| 难度分布 | easy: 7, medium: 14, hard: 16 |
| 平均 scaffold ADL 行数 | ~800 行 |
| 平均 gold patch 行数 | ~30 行 |
| 平均 gold patch 涉及文件数 | ~2.5 个 |
| 平均 DTS 覆盖规则数 | 25–35 条/任务（涵盖 L1 schema 校验、L2 引用完整性、L3 工程约束、L4 动态仿真/CPML 排程、L5 几何干涉 + 可建性） |
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
| 反馈类型 | pytest 通过/失败 | pytest + 视觉 | 输入/输出对 | DTS L0-L5 分层（25-35 规则/任务） |
| 多域耦合 | 无 | 有限 | 无 | 电气/热/结构/信号 |
| 几何约束 | 无 | 有限 | 无 | 碰撞/U位/间距 |
| 新任务扩展 | 依赖新 issue | 依赖新 issue | 手写新题 | 自动从 commit 提取 |

Table: 数据集构建范式对比。{#tbl:dataset-comparison}
