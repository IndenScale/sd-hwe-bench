# 10. 结论

本文介绍了 SD-HWE-Bench——首个面向软件定义硬件工程的 AI Agent benchmark。SD-HWE-Bench 贡献了：(1) 一个包含 34 个任务、3 个 canonical 工程、3 个子领域的数据集；(2) 一套 L0-L4 五层 DTS 评分协议；(3) 5 组 Agent 配置的 pass@1 baseline。

主要发现：

- **Actor Gap**：同一模型在不同 Agent 框架下 pass@1 差异高达 20pp（CLI Native 100% vs API Proxy 80%），揭示了 Agent 框架工程质量对 benchmark 结果的系统性影响。SD-HWE-Bench 不仅是模型能力的测试，也是 Agent 工程质量的测试。
- **规范驱动性有效**：任务 requirement 仅描述功能目标、具体规范由 Agent 主动查阅的设计原则，有效区分了"指令遵循"和"工程设计"能力。
- **规则密度充足**：每任务平均 30 条 DTS 规则覆盖 4 层 9 个子类别，反馈信号丰富。
- **难度分布待优化**：easy 任务占比 50% 导致 CLI Actor 结果饱和，需要更多 hard comprehensive 任务。

SD-HWE-Bench 的代码、数据集、评分器和 baseline 结果全部开源，为 Engineering as Code 评测提供标准化基础设施。
