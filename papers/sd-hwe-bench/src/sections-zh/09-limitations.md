# 9. 局限性与未来工作

## 9.1 领域覆盖

当前 SD-HWE-Bench 仅覆盖 telecom 领域（机柜扩容、数据中心、户外基站三个子领域）。其他硬件工程领域（机械结构、PCB 设计、管道系统、HVAC）尚未纳入。多领域扩展需要构建新的 canonical 工程和对应的 DTS 规则插件，这是明确的未来工作方向。

## 9.2 任务难度分布

v1 数据集中 easy 占 50%（17/34），hard 仅 4 个（12%）。v2 改进后 46 个任务中 easy 占 39%（18/46），hard 占 15%（7/46），分布有所改善。。easy 任务中 5 个复合 easy 任务（telecom-easy-compound-*）已将依赖链从 1-2 层增加到 3-4 层，一定程度上缓解了饱和问题。，Agent 只要正确遵循规范文档中的字段名即可通过。这导致 CLI Native Actor 在全部任务上达到 100% pass@1，pass@1 指标在当前任务集上趋于饱和。

改进方向：已新增 3 个跨专业综合任务（telecom-cross-*）和 4 个涌现约束任务（telecom-emergent-*），初步缓解了区分度不足的问题。未来可继续增加 failure injection 任务和需要跨多个规范文档推断的 hidden constraint 任务。

## 9.3 规则区分度

虽然每个任务平均有 30 条 DTS 规则，但当前规则集中在预防性检查（schema 校验、引用完整性），缺少需要深度推理的压力测试级约束（如全局功率优化、cost-performance tradeoff、多目标 Pareto 优化）。CLI Actor 之所以能 100% 通过，部分原因在于规则在单次生成中容易满足——Agent 只需按规范文档"照章办事"即可。

改进方向：L2 规则已从单层拆分为 L2a/L2b/L2c（v2），每层权重 5%，避免了连锁扣分。未来可引入 multi-rack 全局约束、cross-domain joint constraint、优化类规则（而非单纯的通过/失败检查）。

## 9.4 Actor Gap 的方法论影响

本实验发现同一模型在不同 Agent 框架下表现存在 10-20pp 的系统性差异（Actor Gap，见 §8.1）。这提出了一个重要的方法论问题：benchmark 的评测对象应该是"模型+Agent 框架"组合，而非裸模型。当前的 agentic benchmark 社区缺乏对 Agent 框架的标准化定义和报告规范。SD-HWE-Bench 未来的 leaderboard 将要求投稿者明确报告 Actor 配置（框架、文件系统访问方式、自检循环启用情况）。

## 9.5 模型覆盖

当前 baseline 仅包括 Kimi k2.7 和 DeepSeek-v4（Flash/Pro）两组模型。GPT-4.1、Gemini 2.5、Claude 4 等主流模型尚未评测。扩展模型覆盖是下一步基线实验的优先事项。

## 9.6 pass@5 与 Repair 消融

当前所有数据为 pass@1。pass@5 和 repair ablation 实验（no-repair vs repair 对比）是验证 Information Representation Hypothesis 的关键证据——尚未完成。

## 9.7 可复现性

所有实验在 macOS darwin arm64 环境下运行，DTS 规则在本地 Python 环境执行（`backend=none`）。容器化评分（Docker `sd-hwe-bench-piki:latest`）已就绪但尚未用于所有实验。生产级复现需要使用容器化评分并固定所有依赖版本。
