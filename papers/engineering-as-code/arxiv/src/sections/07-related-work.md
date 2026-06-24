# 7. 相关工作

本章将 EaC 定位于五条研究脉络中：RLVR 训练方法论、工程领域基准、声明式建模与形式化方法、AI4E 实现路线，以及 Infrastructure as Code。

## 7.1 RLVR 方法论

EaC 的信息表示假说直接锚定于 RLVR 文献。DeepSeek-R1 证明了群组相对策略优化（GRPO）加确定性验证信号可产生强大的推理改进 [@deepseek2025r1]。SWE-RL 证明测试套件反馈本身足以训练有效的代码修复 Agent [@sweagent2025swerl]。Multi-SWE-bench 将这一范式扩展到多语言环境，验证其跨语言通用性 [@multiswebench2025]。这些工作确立了 RLVR 因果链的后半段；EaC 关注前半段——缺少结构化表示时 RLVR 无法启动。

## 7.2 工程 AI Benchmark 与自动合规检查

现存的工程 AI 基准在矩阵中占据不同位置。

**AEC-Bench** 评估 AI 审阅人类创建的图纸——处于 ACC 哲学与 AI 能力评估的交汇点，但不测试设计生成能力 [@galanos2026aecbench]。**EngDesign** 跨越多个设计领域，但在已有 CAD/BIM 工作流定义的任务上评估模型，不要求"Design as Code"中间表示 [@engdesign2025]。

**EDA 基准**（VerilogEval [@liu2023verilogeval]、ChipBench [@chipbench2025]、AMS-IO-Bench [@liu2025amsio]）已受益于"Circuit as Code"基础，展现出高 RLVR 兼容性；其性能水平为 SD-HWE-Bench 在传统工程领域建立"Design as Code"基础后计划达到的目标提供了上界参考。Rule2DRC 进一步验证了"执行验证"理念——规则作为可执行检查而非被动约束——与 SD-HWE-Bench 的 L0–L4 设计对齐 [@kim2025rule2drc]。

**自动合规检查（ACC）** 社区通过 ACC 工具 [@eastman2009acc; @zhang2019acc]，以及近期利用 LLM 进行规范-规则转换的努力 [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm]，持续推进合规自动化。但这些方法仍在下游运行——在设计完成后而非设计时。如 §2.2.1 所论证，模型 ACC 还受困于几何碰撞假阳性和命名依赖翻模两个结构性缺陷，这些缺陷的根因在于几何表示本身的语义局限。

## 7.3 声明式建模与形式化方法

**SysML v2** 以 `part`/`occurrence` 分离、`connection`/`interaction` 关系和基于仓库的版本控制提供了丰富的系统工程建模框架 [@omg2024sysml]。但与 ADL 的方法论分歧是根本性的：SysML v2 面向人类 GUI 建模，真相源在模型仓库中，验证以模型检查形式进行；ADL 面向 Agent-人类文本协作，真相源在 YAML 文件中，验证以分层 ESA 规则引擎在提交前执行。这与 Verilog 网表 vs. 电路原理图的分工同构。

**BIM/IFC** 以 IFC 交换格式和几何为中心的模型作为互操作性层 [@buildingsmart2023ifc]。但 IFC 将身份、几何和关系耦合在一个允许多种等价序列化的图中，使行级版本控制困难 [@liu2023ifcversion]。ADL 反转了这种关系：文本是真相源，CAD/BIM 是下游消费者。

**IaC** 提供了软件领域最接近的概念类比，但作用于已为数字态的基础设施状态 [@morris2022iac; @quattrocchi2023iacsurvey]。Chiari 等人的 IaC 静态分析实证 [@chiari2024iacstatic] 直接支持了 EaC 的"X as Code + 静态分析"可行性论证。

## 7.4 AI4E 的实现路线

当前 AI4E 主要有两条实现路线：

- **CUA（Computer-Using Agent）**：让 AI 通过 GUI 操作 CAD 软件。该路径面临界面操作的脆弱性、验证信号缺失与难以规模化试错等局限。
- **CAD-MCP**：在 CAD 软件上封装结构化工具接口。虽然比 CUA 更稳定，但绑定专有 CAD 内核，且未解决设计真相源问题。

EaC 与上述两条路线的方法论相反：以可计算的工程描述为中心，使 CAD/CAE 等工具成为该描述的下游消费者和渲染器。CUA 和 CAD-MCP 是对现有工具链的修补，EaC 则从表示层重建，使 Agent 直接操作可计算的设计真相源。

## 7.5 相关工作系统化对比

下表从真相源形态、版本控制粒度、验证时机、Agent 友好度等维度将 EaC 与主要相关工作系统化对比：

| 维度 | ACC | CUA | CAD-MCP | BIM/IFC | SysML v2 | **EaC（本文）** |
|------|-----|-----|---------|---------|----------|----------------|
| 真相源形态 | CAD/BIM 模型 | CAD GUI | CAD 内核 | 中心模型文件 | 模型仓库 | **文本文件（YAML）** |
| 验证时机 | 设计完成后 | 无 | 工具级 | 设计完成后 | 模型级 | **设计时（ESA）** |
| 验证速度 | 秒至分钟 | 不适用 | 依赖工具 | 分钟级 | 模型检查级 | **毫秒级** |
| 版本控制 | 文件级 | 文件级 | 文件级 | 模型版本 | 模型版本 | **Git 行级** |
| Agent 友好度 | 否 | 间接 | 部分 | 否 | 部分 | **是（一等公民）** |
| 质量左移 | 否（终点） | 否 | 否 | 否（终点） | 部分 | **是（全谱段）** |
| 部件复用 | 临时 | 否 | 否 | 有限 | 部分 | 未来工作 |
| RLVR 兼容性 | 否 | 否 | 否 | 否 | 部分 | **是（L0–L4a，秒级）** |
| 检查语义层级 | 命名约定 | 不适用 | 工具 API | 属性集 | 模型元素 | **Family 类型系统** |
| 假阳性抑制 | 无（纯几何） | 不适用 | 不适用 | 无（纯几何） | 部分 | **Mate 关系排除** |

Table: EaC 与主要相关工作的系统化对比。{#tbl:related-work}
