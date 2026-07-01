# 7. 相关工作

## 7.1 软件工程 Agent 评测

SWE-bench 及其后续工作证明，真实软件 issue 可以被转化为可执行评测任务。其成功依赖代码作为可提交表征、测试套件作为可执行约束、GitHub 作为真实任务来源，以及 patch/review/test 形成的高频闭环。本文并不简单将 SWE-bench 迁移到硬件或工程领域，而是抽象其底层机制：agent 评估需要一个稳定的 substrate。系统级工程缺少的正是代码、测试和版本控制在软件工程中共同扮演的角色。

## 7.2 AI for Engineering 与工程设计 Benchmark

现有 AI for Engineering benchmark 常聚焦数学题、设计问答、CAD 生成、仿真代理模型或特定优化问题。它们各自有价值，但往往缺少完整工程提交、跨文件引用、可执行约束、结构化诊断和 repair loop。本文强调 pseudo-correctness：自然语言方案或孤立几何模型可能看起来合理，却没有完成工程闭合。EaC substrate 的目标是把工程任务变成可执行、可诊断、可复现的 agent evaluation。

## 7.3 Tool Use、MCP 与 CUA

MCP 和 CUA 扩展了 agent 访问外部工具、文档、数据库和 GUI 的能力。本文将它们视为重要接口层，但接口层不等于 evaluation substrate。工具调用可以帮助 agent 查询或操作系统，却不必然定义统一提交对象、确定性 critic、归档协议和 repair 环境。EaC 可以与 MCP/CUA 共存，但它关注的是工具调用之后的工程状态如何被提交和评分。

## 7.4 CAD、BIM、OpenSCAD 与参数化设计

CAD/BIM 是工程行业的核心工具，OpenSCAD、Grasshopper、Dynamo、Revit family 和 Excel 模板展示了参数化设计的长期价值。本文不否定这些路径，而是指出它们通常以生成、几何或单工具协作为中心。Engineering as Code 进一步要求文本表示不仅表达形状或参数，还表达工程对象、引用、连接、约束、调度、交付物和诊断，使其成为 agent evaluation 的闭环表征。

## 7.5 PDK、DTCO 与知识基础设施

半导体 PDK 展示了知识形式化基础设施如何支持跨组织、跨工具、跨抽象层优化。PDK 的关键不是把 PDF 发给设计者，而是把工艺能力转化为 EDA 可消费的规则、模型、参数和库。本文将这一思想推广为系统级工程 AI 的知识基础设施：没有 PDK-like 机制，设备、材料、工艺、气候、电价、供应链和施工知识难以被 agent 消费，评估只能停留在保守合规，难以度量前沿优化能力。
