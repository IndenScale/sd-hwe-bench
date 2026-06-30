# 7. 相关工作

## 7.1 软件工程评测

SWE-bench 及其后续工作证明，真实软件 issue 可以被转化为可执行评测任务。其成功依赖代码作为可计算表征、测试套件作为可执行约束、GitHub 作为真实任务来源。本文并不简单将 SWE-bench 迁移到硬件领域，而是分析为什么系统级工程缺少相同闭环。

## 7.2 AI for Engineering 与工程设计 benchmark

现有 AI for Engineering benchmark 常聚焦数学题、设计问答、CAD 生成、仿真代理模型或特定优化问题。它们各自有价值，但往往缺少完整工程提交、跨文件引用、可执行约束和 repair loop。本文强调 pseudo-correctness：自然语言方案或孤立几何模型可能看起来合理，却没有完成工程闭合。

## 7.3 Tool Use、MCP 与 CUA

MCP 和 CUA 扩展了 Agent 访问外部工具和 GUI 的能力。本文将它们视为重要接口层，但认为接口层不等于评估表征。若没有统一提交对象、确定性 critic 和可复现 repair 环境，工具调用仍难形成严肃 benchmark。

## 7.4 CAD、BIM、OpenSCAD 与文本化工程

CAD/BIM 是工程行业的核心工具，但常以几何和文档协作为中心。OpenSCAD 等 code-like geometry 工具展示了文本化几何的优势。Engineering as Code 进一步要求文本表示不仅表达形状，还表达工程对象、关系、约束、调度和交付物。

## 7.5 PDK、DTCO 与知识基础设施

半导体 PDK 展示了知识形式化基础设施如何支持跨组织、跨工具、跨抽象层优化。本文将这一思想推广为系统级工程 AI 的知识鸿沟：没有 PDK-like 机制，前沿设备、材料、工艺和运营知识难以被 Agent 消费，优化只能停留在保守规则内。
