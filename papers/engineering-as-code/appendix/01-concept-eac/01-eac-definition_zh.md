<!-- markdownlint-disable MD041 -->
<!--
# 01 Eac Definition
位置：附录 I-A — EaC 形式化定义
字数：约 380 词
目标：附录
-->

# EaC 的形式化定义

**Engineering as Code（EaC）** 是一种工程设计范式，要求设计意图以结构化文本声明的形式表达，以自动化规则引擎作为质量门禁，并以版本控制系统与包管理系统作为协作基板。在此范式下，CAD、BIM 与仿真工具仍然作为可视化、深度分析与制造交付的下游工具存在，但设计意图的创建、校验与演化主要发生在文本层。

形式化地，一个 EaC 系统可表示为四元组：

```text
EaC = <ADL, ESA, VCS, PM>
```

其中各分量的含义如下：

- **ADL（Assembly Definition Language）**：装配定义语言，用于声明式设计描述。ADL 以 Part 为原子，通过 PDL、PML、PLL 三个正交子语言分别描述类型、关系与空间布局（详见附录 II）。
- **ESA（Engineering Static Analysis）**：工程静态分析，用于确定性校验。ESA 将合规检查从下游的 Automated Compliance Checking（ACC）前移到设计生成阶段，核心覆盖 L2–L3（引用完整性、业务规则），L4a（快速几何）可作为轻量扩展。L0–L1 属于 ADL 加载期校验，L4b–L6 属于精确几何、物理仿真与人工审批等下游验证（详见附录 III）。
- **VCS（Version Control System）**：版本控制系统，通常指 Git。由于 ADL 声明是纯文本，设计变更可以获得行级历史、分支、语义差异与拉取请求审查。
- **PM（Package Management system）**：包管理系统，例如 EPM（Engineering Package Manager）。PM 负责 Part 库、规则库与生成器的可信复用，类比软件工程中的 npm 或 PyPI。

四元组强调 EaC 不仅是语言或工具，而是一种**社会技术配置**：语言提供表达力，规则引擎提供反馈，版本控制提供协作粒度，包管理提供复用生态。缺少任何一项，范式都无法规模化。

EaC 与现有 CAD/BIM 工作流不是替代关系，而是**主次关系**。文本声明成为设计真相源（source of truth），CAD/BIM 成为该真相源的下游消费者之一——用于渲染、几何精修、制造输出或高保真仿真。这一定位与芯片设计中 Verilog 网表与物理版图之间的关系类似：网表是逻辑设计的真相源，版图是其实现视图 [@ieee1364; @mirhoseini2020rlchip]。

当前 EaC 的知识边界对应于**工程知识成熟度模型**的 Stage III，即“可规则化、可由确定性规则引擎自动校验的工程知识”。Stage I（口传传统）与 Stage II（共识判断）不在 EaC 核心覆盖范围内；Stage IV（仿真可解）则作为未来扩展方向。这一保守定位基于一个稳健原则：若模型连确定性规则都无法满足，则讨论更复杂的模糊约束与仿真校验缺乏基础。
