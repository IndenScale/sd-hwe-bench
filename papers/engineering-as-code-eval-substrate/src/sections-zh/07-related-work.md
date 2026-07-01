# 7. 相关工作

## 7.1 软件工程 Agent 评测

SWE-bench 及其后续工作证明，真实软件 issue 可以被转化为可执行评测任务。其成功依赖代码作为可提交表征、测试套件作为可执行约束、GitHub 作为真实任务来源，以及 patch/review/test 形成的高频闭环。本文并不简单将 SWE-bench 迁移到硬件或工程领域，而是抽象其底层机制：agent 评估需要一个稳定的 substrate。系统级工程缺少的，正是代码、测试和版本控制在软件工程中共同扮演的角色。

## 7.2 ML Evaluation Infrastructure

本文也位于 ML evaluation infrastructure 的演化线上。早期 NLP 自动评估大量依赖 reference-based static metrics，例如机器翻译中的 BLEU 和摘要任务中的 ROUGE。这类指标使大规模比较成为可能，但也暴露了静态相似度指标难以刻画真实任务成功的问题。代码生成和软件 agent 评估随后把评估单元从表面相似度转向 executable correctness：HumanEval 用单元测试度量函数正确性，SWE-bench 用真实 GitHub issue、repository patch 和测试结果评估 agent 是否解决真实软件问题。

强化学习领域更早形成了 environment interface 传统。Gym-style 环境将 state、action、reward、termination 和 benchmark protocol 标准化，使 agent 能在可复现实验环境中交互、学习和比较。这个传统说明，评估不只是指标函数，也可以是一个可执行环境；环境的状态表示、动作空间、反馈延迟和奖励结构会塑造科学结论。

EaC 沿着这条演化线前进，但面对的是一个 evaluation substrate 并非天然存在的领域。在软件中，代码仓和测试定义了自然的 patch-and-check loop；在 RL 中，环境暴露了标准交互 API；在 IC/EDA-oriented HWE benchmarks 中，RTL、schematic、simulator、testbench 和 datasheet 已经提供局部可执行底座。系统级工程领域则缺少这样的统一底座：状态、约束和知识分散在 CAD/BIM、表格、PDF、GUI、供应商手册、仿真软件和人工审查流程中。因此，EaC 关心的是当软件式测试套件、RL 式环境接口和 EDA 式验证流都不是默认存在时，engineering agents 的 evaluation substrate 应该提供什么。

## 7.3 AI for Engineering 与工程设计 Benchmark

现有 AI for Engineering benchmark 常聚焦数学题、设计问答、CAD 生成、仿真代理模型或特定优化问题。它们各自有价值，但往往缺少完整工程提交、跨文件引用、可执行约束、结构化诊断和 repair loop。本文强调 pseudo-correctness：自然语言方案或孤立几何模型可能看起来合理，却没有完成工程闭合。EaC substrate 的目标是把工程任务变成可执行、可诊断、可复现的 agent evaluation。

## 7.4 为什么现有 HWE Benchmark 能成立

近期硬件工程 benchmark，尤其是 IC/EDA 和板级电路方向的 HWE-Bench，提供了一个重要正例：当某个工程领域已经拥有 code-like representation、executable verification 和 tool-consumable knowledge 时，agent benchmark 可以成立。第 2 章已将它们作为 positive control 纳入 failure analysis；本节只补充其与本文的关系。

Repository-level RTL bug repair HWE-Bench 将真实硬件 bug-fix PR 转化为任务，覆盖 Verilog/SystemVerilog/Chisel 项目，并在容器化环境中通过项目原生仿真与回归流程验证修复。这类任务天然拥有可提交对象：agent 输出 repository patch；也天然拥有可执行 critic：编译、仿真、testbench 和 fail-to-pass regression；还拥有可被工具链消费的知识：RTL 语义、配置、验证组件、ISA/spec、EDA flow 和项目文档。

Board-level schematic HWE-Bench 则让模型基于功能需求和 IC datasheets 生成原理图，再通过 static electrical rules 和 circuit simulation 检查动态行为。这里同样存在局部闭环：schematic/netlist 是提交对象，ERC 与仿真是 critic，datasheet 和电路模型提供知识来源。

因此，已有 HWE benchmark 不应被视为本文的反例，而应被视为动机证据。它们在窄而重要的硬件任务中实例化了本文所说的 substrate 条件；本文的问题是如何在没有天然 EDA/PDK/testbench substrate 的系统级工程中，显式构造类似的 evaluation substrate。

## 7.5 Tool Use、MCP 与 CUA

MCP 和 CUA 扩展了 agent 访问外部工具、文档、数据库和 GUI 的能力。本文将它们视为重要接口层，但接口层不等于 evaluation substrate。工具调用可以帮助 agent 查询或操作系统，却不必然定义统一提交对象、确定性 critic、归档协议和 repair 环境。EaC 可以与 MCP/CUA 共存，但它关注的是工具调用之后的工程状态如何被提交和评分。

## 7.6 CAD、BIM、OpenSCAD 与参数化设计

CAD/BIM 是工程行业的核心工具，OpenSCAD、Grasshopper、Dynamo、Revit family 和 Excel 模板展示了参数化设计的长期价值。本文承认这些路径的价值，同时指出它们通常以生成、几何或单工具协作为中心。Engineering as Code 进一步要求文本表示不仅表达形状或参数，还表达工程对象、引用、连接、约束、调度、交付物和诊断，使其成为 agent evaluation 的闭环表征。

## 7.7 PDK、DTCO 与知识基础设施

半导体 PDK 展示了知识形式化基础设施如何支持跨组织、跨工具、跨抽象层优化。PDK 的关键不在于把 PDF 发给设计者，而在于把工艺能力转化为 EDA 可消费的规则、模型、参数和库。本文将这一思想推广为系统级工程 AI 的知识基础设施：没有 PDK-like 机制，设备、材料、工艺、气候、电价、供应链和施工知识难以被 agent 消费，评估只能停留在保守合规，难以度量前沿优化能力。
