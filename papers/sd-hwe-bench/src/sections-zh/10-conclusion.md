# 10. 结论

本文提出 **SD-HWE-Bench**，首个面向声明式硬件工程的大规模可执行 benchmark。我们指出，硬件工程 AI 的瓶颈不在于模型能力，而在于缺乏可计算表示层与可高频迭代的评估基础设施——即"可计算表示缺口"（representation gap）。

为填补这一缺口，我们采用 Engineering as Code 范式，通过以下设计构建了 SD-HWE-Bench：

1. **ADL（Assembly Definition Language）** 作为硬件工程的文本原生可计算表示，以 Part 为原子、PDL/PML/PLL 三层正交分离设计意图的声明。
2. **DTS（Design Test Suite）** 作为分层确定性评分引擎，从 L0 语法到 L4/ADA 动态分析提供毫秒至秒级的执行评测。
3. **Canonical 工程 + Commit 提取**作为任务生成范式，确保任务的真实性、设计增量的完整性和评测的可复现性。
4. **多 Actor 抽象 + 统一 Critic 层**作为实验平台，支持多种 LLM Agent 的可比评测。

实验和消融分析验证了两个核心命题：

- **物理工程设计对当前 LLM Agent 具有显著挑战性**：在完整上下文下，最强基线的 pass@1 仅为 xx%，失败主要源于设计逻辑遗漏（L3）而非语法/类型错误。
- **确定性反馈具有因果价值**：引入 DTS repair loop 后通过率提升 xx pp，证明"Agent 知道该怎么做，但需要反馈信号来自我修正"的工程认知。

SD-HWE-Bench 的价值不仅在于当前的评测结果，更在于它所验证的范式：通过将物理工程设计转化为可计算、可版本化、可自动验证的代码表示，我们能够把为软件工程优化的训练与评估基础设施对齐到硬件工程领域。这为 RLVR 训练提供了**稠密确定性奖励生境**（dense verifiable reward environment），并为物理工程 AI 建立了**可复现、可迭代、可比较**的评测标准。

我们开源了 canonical ADL 工程、任务提取工具、DTS 评测 harness 和容器化复现环境，诚邀社区共同推动这一方向——**让 Agent 学会像工程师一样在约束中设计**。
