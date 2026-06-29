# 3. Benchmark 设计

本章阐述 SD-HWE-Bench 的整体设计理念、核心组件和任务生命周期。第 3.1 节回顾 Engineering as Code 范式的关键概念；第 3.2 节介绍 benchmark 的三层架构；第 3.3 节描述任务的定义、来源和质量保证机制；第 3.4 节介绍 Actor 抽象与评测流程。

## 3.1 Engineering as Code 核心概念

SD-HWE-Bench 建立在 **Engineering as Code（EaC）** 范式之上 [@song2025eac]。EaC 的核心主张是：物理工程设计的瓶颈不在于模型能力，而在于缺乏像代码一样的可计算设计表示。该范式包含三个相互耦合的组件：

### 3.1.1 ADL：Assembly Definition Language

**ADL** 是一种声明式领域特定语言，用于统一描述物理工程设计。它用文本原生方式建模"部件是什么、部件间关系、部件如何布局"三大维度。ADL 包含三层正交子语言：

- **PDL（Part Definition Language）**：定义部件类型。每个 Part 是一个类型化实体，包含端口（电气/流体/机械/信号）、属性（功率、重量、尺寸、材料等）和兼容性约束（接口类型、兼容引脚族等）。Example：`PDL` 文件中定义一个48端口交换机 Part，声明其电源端口类型为 `C14`、功耗 350W、重量 4.2kg。
- **PML（Part Mating Language）**：定义部件间关系。声明式描述部件之间的电气连接（电源线/信号线/数据线）、物理配合（螺栓连接/卡扣/导轨安装）和层级包含（子装配→父装配）。Example：`PML` 文件中定义一个 Switch 的上行端口连接到 PatchPanel 的第 1-24 端口，指定连接类型为 `LC-Duplex`。
- **PLL（Part Layout Language）**：定义部件的空间布局。声明式描述部件在三维空间中的位置、方向、以及布局约束（如机柜 U 位范围、间距、碰撞避免）。Example：`PLL` 文件中定义 Switch 从 U25 到 U26 位安装，并声明不得与相邻设备的散热空间冲突。

这三层子语言正交分离：修改 Part 的功率属性不会影响其布局声明；修改布线关系不需要重写 Part 定义。这种正交性是后续 DTS 分层检查的架构基础。

### 3.1.2 DTS：Design Test Suite

**DTS（Design Test Suite）** 是 EaC 的质量门引擎——它将设计规则检查前移到设计生成阶段，为 Agent 提供分层确定性反馈。与传统的 Automated Compliance Checking（ACC）不同，DTS 检查的是设计声明（ADL 文本）而非几何实例化产物，因而天然避免了假碰撞和命名依赖等问题。

DTS 的分层对应 §5 评测协议中详述的 L0–L6 层。这里先给出概念性概述：

- **L0（语法层）**：YAML 合法性、项目非空、必需文件与交付物存在性。缺少 `expected_files` 或 `expected_deliverables` 属于语法/生成失败。
- **L1（语义层）**：Schema 校验、类型系统一致、属性合法范围。
- **L2（引用完整性）**：Part 引用可解析、端口匹配、配合/目录引用、层级无循环。
- **L3 / ASA（装配体静态分析）**：基于声明对物理装配体做静态断言——功率预算、U 位冲突、端口兼容性、散热间距等。不施加激励，看声明即可判断对错。
- **L4 / ADA（装配体动态分析）**：施加虚拟激励 → 观察系统响应 → 阈值判断。AIDC 设计任务中体现为 8760h/48h 热/电/LCC 仿真合规检查；EPC 任务中体现为 CPML 施工排程仿真（工期、资源、应急预案）；未来可扩展防火、承重、电压降等。其形式等价于 setup → exercise → assert 的标准 test case。
- **L5（几何干涉、误差分析与施工可建性）**：几何碰撞、rack 空间、装配误差、吊装方案、VDC 工作面等。
- **L6（高精度物理仿真，预留）**：FEM/CFD 等高保真仿真，本次未启用。

**Performance Score** 与 **Rubric** 是诊断性指标，不占用层号、不计入 overall_score。交付物缺失归并到 L0 失败。

DTS 在 SD-HWE-Bench 中扮演双重角色：(1) 作为评分器（Critic），为 Agent 输出提供确定性评分；(2) 作为 repair 反馈信号，Agent 可根据 DTS 错误报告迭代修复设计。

### 3.1.3 piki：EaC 的开源运行时

**piki** 是 EaC 范式的开源参考实现，提供 ADL 解析、DTS 检查和交付物生成（如 BOM 表、3D 预览、布线图）等核心功能。SD-HWE-Bench 使用 piki 作为评分引擎和容器化执行环境（参见 §3.4）。

## 3.2 Benchmark 三层架构

SD-HWE-Bench 的整体架构分为三层（图 1）：

```text
┌─────────────────────────────────────────────────┐
│                 Task Layer                       │
│  tasks/<domain>/<task>/                          │
│  ├── task.yaml     (元数据、需求、评分定义)       │
│  ├── scaffold/     (Agent 初始上下文)             │
│  │   ├── piki.toml                              │
│  │   └── models/   (PDL/PML/PLL 部分文件)        │
│  └── solution/     (参考方案，对 Agent 隐藏)      │
└──────────────────┬──────────────────────────────┘
                   │ 输入
┌──────────────────▼──────────────────────────────┐
│               Agent (Actor) Layer                │
│  Actor 基类 → Kimi / Gemini / Codex / OpenAI     │
│  run(prompt, workspace_root) → ActorResult       │
│  独立修改 workspace 中的 ADL 文件                │
└──────────────────┬──────────────────────────────┘
                   │ 输出 (ADL patch)
┌──────────────────▼──────────────────────────────┐
│              Review (Critic) Layer               │
│  SyntaxCritic(L0) → PikiCritic(L1-L5)            │
│  → AIDC Simulation / CPML Schedule(L4) → Deliverable │
│  → PerformanceScore(diagnostic) → RubricCritic(LLM) │
│  统一入口: score_task(workspace, task) → ScoreResult │
└─────────────────────────────────────────────────┘
```

**Figure 1**：SD-HWE-Bench 三层架构。Task Layer 定义任务输入和 ground truth；Agent Layer 执行设计生成；Critic Layer 提供多层确定性评分。{#fig:architecture}

### 3.2.1 Task Layer

每个任务是一个自包含目录，包含：

- `task.yaml`：任务元数据（id、类型、难度、需求、期望文件、评分层、rubrics）。
- `scaffold/`：Agent 可见的初始 ADL 工程——类似 SWE-bench 任务中的代码库 snapshot。
- `solution/`：参考 patch（对 Agent 隐藏），包含 gold 方案的内容、修改范围、预期 DTS 结果。

### 3.2.2 Agent Layer

Agent Layer 封装不同的 LLM Agent 后端。当前支持四种 Actor：

| Actor 标识 | 模型 | 调用方式 | 说明 |
|-----------|------|---------|------|
| `kimi[:model]` | Kimi Code | `kimi -p <prompt>` | CLI Agent，直接修改工作目录 |
| `codex[:model]` | DeepSeek 等 | `codex exec ...` | Codex CLI Agent |

所有 Actor 实现统一接口 `run(prompt, workspace_root) → ActorResult`，产出物为标准 ADL YAML 文件。

### 3.2.3 Critic Layer

Critic Layer 对 Agent 输出进行分层确定性评分与诊断。执行顺序为：

1. **SyntaxCritic (L0)**：YAML 合法性、项目非空、`expected_files` 与 `expected_deliverables` 存在性。
2. **PikiCritic (L1–L5)**：调用 `piki check --format json`，将规则失败映射到 DTS 各层（详见 §5）。AIDC 设计任务的仿真硬约束映射到 L4；detailed-design / epc 任务的可建性检查由 `ConstructabilityCritic` 补充并合并到 L5。
3. **NumericCritic (L3)**：对 `numeric_asserts` 进行数值校验，失败会翻转对应 L3 规则。
4. **DeliverableCritic**：调用 `piki generate` 检查 `dist/` 下是否生成期望交付物。交付物生成失败会导致任务 unresolved，但不单独设评分层。
5. **PerformanceCritic / EPCCritic (Diagnostic)**：对 AIDC 设计任务计算 `performance_score`（相对 baseline/reference 的 PUE/TCO 改善），对 EPC 任务计算 P90 工期/成本改善；仅作诊断，不计入 overall_score。
6. **RubricCritic (LLM-as-Judge)**：按 task.yaml 中定义的 rubrics 维度进行定性评估（诊断性，不计入 overall_score）。

统一评分入口 `score_task()` 聚合上述结果。

## 3.3 任务定义与质量保证

### 3.3.1 任务类型

SD-HWE-Bench 定义了八种任务类型，覆盖硬件工程设计的核心能力维度：

- **instance-declaration**：实例声明——根据需求创建 Part 实例，填写属性（功率、型号、端口）。
- **layout-design**：布局设计——在三维空间中分配 Part 位置，满足 U 位、间距、散热等约束。
- **connection-design**：连接设计——声明 Part 之间的电气/流体/信号连接关系。
- **mating-design**：配合设计——声明 Part 之间的物理配合关系（螺栓/卡扣/导轨）。
- **comprehensive**：综合设计——同时涉及上述多类能力。
- **incremental**：增量修改——在已有设计上做出局部改动。
- **co-design**：协同设计——同时优化系统设计与运营策略（如 AIDC 设计-调度联合优化）。
- **detailed-design**：详细设计——在概念设计基础上补充几何、吊装、VDC 工作面等施工可建性信息。
- **epc**：工程总承包——使用 CPML 进行施工排程、资源规划与风险响应。

每个任务还标注 `difficulty`（easy / medium / hard），基于所需修改的文件数、涉及的 DTS 层数和跨域耦合程度判定。

### 3.3.2 任务来源：Canonical 工程 + Commit 提取

参考 SWE-bench 的任务生成范式，SD-HWE-Bench 的任务来自**canonical ADL 工程**的 commit 历史。Canonical 工程是由领域专家精心构建的完整 ADL 工程，其 commit 历史模拟真实设计迭代——每个 commit 是一个有意义的完整增量（如"增加第 4-6 台交换机并更新 power budget"）。

任务提取 pipeline（`tools/extract_tasks.py`）从两个相邻 commit 之间的差异自动生成任务：

- **问题描述**：基于 commit message 和 diff 内容自动生成自然语言需求。
- **初始上下文（scaffold）**：checkout 到 commit k 的状态。
- **参考方案（solution）**：commit k+1 的完整状态，包括新增/修改的 ADL 文件。
- **DTS 测试信号**：在 solution 上运行 `piki check`，确保其通过所有 DTS 层。

每个自动提取的任务随后经过人工审核：确认问题描述准确、scaffold 完整、solution 正确且通过 piki check。不符合标准的任务被剔除或手动修正。

## 3.4 Actor 抽象与评测流程

### 3.4.1 Actor 接口

所有 Actor 实现统一的 Python 接口：

```python
class Actor(ABC):
    @abstractmethod
    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        """在 workspace_root 上执行设计任务。
        Agent 可直接修改 workspace 中的文件。
        返回 ActorResult 包含输出路径、日志和交互轨迹。"""
        ...
```

这种抽象保证了新 Actor 可即插即入——只需实现 `run()` 方法即可接入评测 pipeline。

### 3.4.2 评测流程

每次 rollout（一次 Actor 执行）的完整评测流程如下：

1. **Prepare**：为任务创建隔离的 workspace（`--sandbox auto` 默认在容器中执行 piki check/generate；Agent 生成阶段在本地工作目录）。
2. **Scaffold**：将 `scaffold/` 复制到 workspace。
3. **Prompt**：构建包含任务需求、ADL 使用指南、DTS 层次说明、输出格式要求、可用工具列表的完整 prompt。
4. **Run**：Actor 执行 `run(prompt, workspace)`，输出修改后的 ADL 文件。
5. **Score**：依次运行 `SyntaxCritic` → `PikiCritic` → `NumericCritic` → `ConstructabilityCritic` → `DeliverableCritic` → `PerformanceCritic` / `EPCCritic` → `RubricCritic`。
6. **Archive**：将滚动结果写入 `runs/<timestamp>_<task-id>_<actor>_<model>/`，包含 `manifest.json`、`prompt.md`、`trajectory.jsonl` 和 `workspace/`。

对于 `--passes N`，上述流程独立重复 N 次（每次使用新的 workspace），用于估算 pass@k。

### 3.4.3 容器化环境

为确保评分结果的可复现性，所有 `piki check` 和 `piki generate` 调用默认在容器中执行（`--sandbox auto` 自动探测 docker/podman，回退到 `none` 仅作调试用）。容器 image `sd-hwe-bench-piki:latest` 包含固定版本的 piki 运行时、Python 环境和依赖，消除了本地环境差异对评分的影响。

Agent 生成阶段不强制容器化——不同类型的 Actor 有不同的运行需求。但评分阶段始终统一在容器内执行，确保不同 Actor 的评分标准完全一致。

SD-HWE-Bench 进一步采用 **thin sandbox** 模式隔离评分环境：Agent 不直接获得沙盒的控制权，而是通过 `sd-hwe-bench` CLI 的固定接口请求 `piki check` 和 `piki generate`。沙盒内的规则引擎、测试用例和评分逻辑对 Agent 完全不可写。这一设计有两个目的：(1) 防止 Agent 通过篡改 DTS 规则或测试文件进行 reward hacking；(2) 确保所有 Actor 在同一套不可变评分标准下接受评测，而非各自在可修改的本地环境中运行。
