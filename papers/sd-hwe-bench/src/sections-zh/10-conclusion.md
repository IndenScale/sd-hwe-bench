# 10. 结论

本文介绍了 SD-HWE-Bench——首个面向软件定义硬件工程的 AI Agent benchmark。SD-HWE-Bench 贡献了：(1) 一个包含 37 个任务、5 个 canonical 工程、4 个子领域（电信机柜、数据中心、户外基站、AIDC）的数据集；(2) 一套 L0–L6 六层 DTS 评分协议（L0–L5 为确定性 QA 层，L6 预留为高精度物理仿真）；(3) 2 组 CLI Native 配置的 pass@1 baseline。

主要发现：

- **规范驱动性有效**：任务 requirement 仅描述功能目标、具体规范由 Agent 主动查阅的设计原则，有效区分了"指令遵循"和"工程设计"能力。
- **规则密度充足**：每任务平均 25–35 条 DTS 规则覆盖 L1–L5 五个层次，反馈信号丰富。
- **AIDC 引入优化区分度**：通过 Performance Score 诊断指标，AIDC 任务能够量化 Agent 在 PUE/TCO 等目标上的改善幅度，而不仅限于二元通过/失败。
- **难度分布改善**：hard 任务占比已提升至 43%，CLI Native Actor 在 30 任务上 pass@1 为 84–87%，任务集具备有效区分度。

SD-HWE-Bench 的代码、数据集、评分器和 baseline 结果全部开源，为 Engineering as Code 评测提供标准化基础设施。
