# 2. 相关工作

本章按三层递进结构组织：首先回顾 LLM 评测与 Agent benchmark 的演进趋势，然后聚焦软件工程 benchmark 的"可计算表示 + 执行评测"范式，最后分析硬件工程领域 AI 工作的现状与系统性瓶颈。

## 2.1 LLM 评测与 Agent Benchmark

早期 LLM 评测多集中于知识问答、推理与文本生成 [@hendrycks2021measuring; @srivastava2022bigbench]。随着模型能力提升，研究者转向更具交互性与工具使用能力的 Agent benchmark。GAIA [@mialon2023gaia] 评估多模态 Agent 在 Web 环境中的实时推理能力；OSWorld [@xie2024osworld] 构建桌面操作系统交互任务；WebArena [@zhou2024webarena] 提供 Web 环境下的端到端任务。此外，SWE-bench [@jimenez2024swebench] 将评测提升到仓库级，要求 Agent 在真实代码库中按 GitHub issue 修改代码并通过测试。

这些 benchmark 的共同趋势是从"静态问答"走向"可执行评测"——即 Agent 的输出必须通过可自动验证的执行结果来判定正确性。SD-HWE-Bench 继承这一趋势，将可执行评测从代码领域扩展到物理工程设计领域。

## 2.2 软件工程 Benchmark：可计算表示 + 执行评测的成功范式

软件工程领域已经证明，"可计算表示 + 执行评测"能够极大加速 AI 研究。HumanEval [@chen2021evaluating] 与 MBPP [@austin2021mbpp] 开创了函数级代码生成评测；随后，SWE-bench [@jimenez2024swebench] 将任务规模提升到仓库级，要求模型根据 GitHub issue 修改真实代码库并通过完整的 QA 套件（linter、编译器、静态分析、单元测试、集成测试）。SWE-bench Multimodal [@yang2025swebm] 进一步引入视觉元素与 JavaScript 领域；SWE-agent [@yang2024sweagent] 从系统角度推动代码智能体发展。

这些工作的共同范式是：任务输入/输出均为文本，评测完全自动化，且与现有软件开发基础设施（Git、Docker、pytest）高度兼容。SD-HWE-Bench 借鉴了这一范式——将上下文从代码库替换为 ADL 工程，将测试/验证反馈从 QA 套件（linter → 编译器 → 类型检查 → 单元测试 → 集成测试）扩展为 DTS 分层断言。核心区别在于：软件工程中代码天然可执行；硬件工程中必须先建立可计算表示层（ADL），然后才能实现类似的可执行评测闭环。

@tbl:benchmark-comparison 对比了 SD-HWE-Bench 与代表性 benchmark 的关键维度。

| 维度 | HumanEval | SWE-bench | SWE-bench M | SD-HWE-Bench |
|------|-----------|-----------|-------------|-------------|
| 领域 | 代码 | 代码 | 代码+UI | 物理工程 |
| 任务类型 | 函数生成 | 仓库级修复 | 仓库级修复+视觉 | 设计增量 |
| 任务来源 | 手写命题 | GitHub issue | GitHub issue | Canonical 工程 commit |
| 执行评测 | ✅ QA 套件 | ✅ QA 套件 | ✅ QA 套件+视觉 | ✅ DTS 分层断言 |
| 多域耦合 | ❌ | ❌ | 有限 | ✅ 电源/热/结构/信号 |
| 几何约束 | ❌ | ❌ | 有限 | ✅ 碰撞/U位/间距 |
| 长上下文 | ❌ | ✅ | ✅ | ✅ |
| 反馈延迟 | 秒级 | 秒级 | 秒级 | 毫秒级(L0-L2)/秒级(L3-L4) |
| 确定性奖励 | ✅ | ✅ | 部分 | ✅ 全分层 |

Table: SD-HWE-Bench 与代表性 benchmark 的对比。{#tbl:benchmark-comparison}

## 2.3 硬件工程中的 AI：IC/DEA 的例外与系统级/设备级的碎片化

在硬件工程中，集成电路（IC）与数字电子自动化（DEA）是相对成功的分支。这得益于其成熟的可计算表示：RTL（Verilog/VHDL）、网表、LEF/DEF、SDC、GDSII 等；以及日益成熟的开放工具链：Yosys [@wolf2016yosys]、OpenROAD [@ajayi2019openroad]、OpenRAM 等。基于这些基础设施，研究者提出了芯片布局优化 [@mirhoseini2021chip]、逻辑综合优化 [@hosny2021logic]、模拟电路设计 [@wang2022analog] 等工作。

然而，这种成功高度特化于 IC/DEA 领域——其繁荣恰恰是因为它拥有成熟的文本化可计算表示和开放工具链。一旦超出 IC 边界，进入**系统级/设备级硬件工程**（如电信机柜部署、数据中心基础设施、机械装配），情况急剧恶化：

- **表示碎片化**：设计数据分散在 CAD 模型（SolidWorks/Creo）、BIM 模型（Revit）、PDF 规格书、Excel BOM 表和商业软件 GUI 中。没有一个统一的、可被 LLM 消费的文本表示。
- **商业软件锁**：现有 EDA/CAE/AEC 工具多为闭源商业软件，缺乏开放 API，无法嵌入 CI 管道或高频 Agent 交互循环。
- **仿真昂贵**：高精度 CFD/FEA/SPICE 仿真一次耗时数小时到数天，无法为 Agent 提供高频 RLVR 反馈。
- **缺乏 benchmark**：AEC-Bench 等少量基准 [@...] 仍依赖几何模型和事后审查，而非可执行的设计声明检查。

这正是我们提出 SD-HWE-Bench 的动机：借鉴 IC/DEA 在语言、格式、协议、工具链上的成功实践，通过 EaC 和 ADL 为系统级/设备级硬件工程建立可计算表示层，进而构建可执行的 benchmark。

---

### 补充说明：IC/DEA 成功的关键因素总结

IC/DEA 之所以能成为硬件工程中 AI 落地的孤例，可归结为三个因素：

1. **可计算语言**：Verilog/VHDL 是文本 Native 的 HDL，可直接被解析、静态分析和版本控制。
2. **开放工具链**：从逻辑综合（Yosys）到物理设计（OpenROAD）到 DRC/LVS（Magic），已形成完整的开放工具栈。
3. **EDA 自动化传统**：自 1980 年代以来，EDA 行业已建立了从 RTL 到 GDSII 的完整自动化和验证闭环，这为 AI 介入提供了天然的接入点。

设备级硬件工程至今缺乏这三层基础设施中的任何一层。SD-HWE-Bench 通过 ADL + DTS + canonical 工程 + 任务提取工具，试图为设备级 HWE 补齐这三大缺口。
