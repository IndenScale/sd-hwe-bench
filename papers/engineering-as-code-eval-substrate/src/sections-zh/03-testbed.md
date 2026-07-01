# 3. EaC Substrate 的当前实现：SD-HWE-Bench

SD-HWE-Bench 在本文中不是单独的 benchmark 主角，而是 Engineering as Code evaluation substrate 的当前实现。它提供四个关键能力：可提交的工程状态、可执行的分层 critic、可复现的任务增量和可观察的 failure mode。

## 3.1 ADL：工程状态作为可提交对象

EaC 的第一层是 ADL，即一种面向系统级工程的声明式设计语言。ADL 用工程对象、属性、引用、连接、配合、布局、调度和交付物表达设计状态，使 agent 的输出不再是一段自然语言方案，而是一个可提交、可 diff、可评分的工程 patch。

这种提交对象与普通配置文件不同。它需要保留工程语义：设备和端口可以被引用，连接和配合可以被检查，位置和几何可以被约束，资源和活动可以进入排程，交付物可以被 critic 验证。ADL 的目标不是覆盖所有工业软件能力，而是在 agent evaluation 中提供稳定的语义接口。

## 3.2 DTS：正确性作为分层可执行 critic

EaC 的第二层是 DTS 分层约束系统。DTS 将工程正确性拆分为多个可执行层：

- L0：语法和文件格式。
- L1：schema 与类型。
- L2：引用完整性。
- L3：静态工程约束，例如功率、接口、载荷和规则断言。
- L4：动态模型、调度仿真或多方案决策。
- L5：几何干涉、空间约束和施工可建性。
- L6：预留高精度 FEM/CFD 等仿真。

这种分层使错误不只是 pass/fail，而能被归因到约束类别、对象和文件位置。它为 repair loop、错误模式分析、诊断粒度实验和 RLVR 奖励设计提供统一信号。

## 3.3 Canonical Lineage：任务作为工程增量

SD-HWE-Bench 从 canonical 工程的 commit 历史中提取任务。每个任务可以理解为一个真实工程增量：给定某个设计状态和需求，agent 需要提交下一个状态的工程 patch。canonical lineage 保留了 scaffold、solution 和任务说明之间的一致性，避免手写任务在多阶段演进中产生内容漂移。

AIDC 60MW reference domain 采用 lineage 化 canonical，将概念设计、详细设计和 EPC 排程组织为同一工程仓的连续 tag。后一阶段物理包含前一阶段，使设计状态、施工状态和运营状态共享单一事实源。这一点对 evaluation substrate 很关键：如果任务之间的真相源漂移，agent 失败就无法被稳定归因。

## 3.4 Actor Isolation：评估作为可审计运行

工程 agent 评估还需要保证提交过程本身可信。SD-HWE-Bench 将 actor 工作区迁出仓库，并在 macOS 上使用 seatbelt 对参考解、canonical、runs 和 leaderboard 进行内核级读取隔离。agent 只能看到 scaffold 和任务说明，评分后产物再归档回 runs。

这使 pass/fail 不依赖“agent 是否偶然读到参考答案”，而依赖其在隔离工作区内生成的工程提交。对于 NeurIPS E&D 这类重视 artifact validity 的场景，隔离、归档和可复现运行不是工程细节，而是 evaluation substrate 的组成部分。

## 3.5 本文如何使用该平台

本文不把任务数量作为主要论据，而把 SD-HWE-Bench 用于受控对照：

1. 在同一工程意图上比较不同表征路径是否能形成可复现评估闭环。
2. 在同一任务池上比较自然语言规范、文档规范和可执行 DTS 的行为差异。
3. 在 AIDC 场景中比较静态合规、局部优化和设计-调度联合优化的上限差异。

这种用法使小规模但高耦合的任务集仍然具有解释力：我们关心的是 evaluation substrate 的因果结构，而不是仅凭任务数量证明覆盖面。
