# 9. 局限性与未来工作

## 9.1 领域覆盖

当前 SD-HWE-Bench 仅覆盖 telecom 领域（机柜扩容、数据中心、户外基站三个传统子领域，以及 AIDC 运营/协同设计）。其他硬件工程领域（机械结构、PCB 设计、管道系统、HVAC）尚未纳入。多领域扩展需要构建新的 canonical 工程和对应的 DTS 规则插件，这是明确的未来工作方向。

## 9.2 任务难度分布

当前 37 个任务中 easy 占 19%（7/37），medium 占 38%（14/37），hard 占 43%（16/37）。相比早期版本，hard 比例已显著提升，但部分 hard 任务（如 comprehensive 阶段任务）仍可通过规范查阅和局部修改完成。CLI Native Actor 在已评测的 30 个任务上达到 84–87% pass@1，说明任务集已具备一定区分度，但尚未饱和。

改进方向：已新增 3 个跨专业综合任务（telecom-cross-*）、4 个涌现约束任务（telecom-emergent-*）和 4 个 AIDC 任务，初步缓解了区分度不足的问题。未来可继续增加 failure injection 任务和需要跨多个规范文档推断的 hidden constraint 任务。

## 9.3 规则区分度

虽然每个任务平均有 25–35 条 DTS 规则，但当前规则集中在预防性检查（schema 校验、引用完整性、静态工程约束），缺少需要深度推理的压力测试级约束（如全局功率优化、cost-performance tradeoff、多目标 Pareto 优化）。AIDC 任务通过 Performance Score 引入了优化类诊断指标，但这些指标目前仅作参考，未计入 resolved 判定。

改进方向：未来可引入 multi-rack 全局约束、cross-domain joint constraint、更复杂的 AIDC 多目标优化规则，并将部分 Performance Score 约束转化为硬约束以提升区分度。

## 9.4 Actor 框架的方法论影响

SD-HWE-Bench 的评测对象是"模型+Agent 框架"组合，而非裸模型。当前的 agentic benchmark 社区缺乏对 Agent 框架的标准化定义和报告规范。SD-HWE-Bench 要求实验明确报告 Actor 配置（CLI 框架、模型、上下文设置），不同配置的结果不可直接比较。

## 9.5 模型覆盖

当前 baseline 仅包括 Kimi k2.7 和 DeepSeek-v4-Pro 两组模型。GPT-4.1、Gemini 2.5、Claude 4 等主流模型尚未评测。扩展模型覆盖是下一步基线实验的优先事项。

## 9.6 pass@5 与 Repair 消融

当前所有数据为 pass@1（5 passes/task，用于估算 pass@1）。pass@5 和 repair ablation 实验（no-repair vs repair 对比）是验证 Information Representation Hypothesis 的关键证据——尚未完成。

## 9.7 可复现性

所有实验在 macOS darwin arm64 环境下运行，DTS 规则在本地 Python 环境执行（`backend=none`）。容器化评分（Docker `sd-hwe-bench-piki:latest`）已就绪但尚未用于所有实验。生产级复现需要使用容器化评分并固定所有依赖版本。

## 9.8 高精度物理仿真

当前 DTS 的 L4 层使用解析公式和轻量代理模型（RC 热网络、包围盒碰撞、简支梁公式）。L6 层预留用于 FEM/CFD 等高精度仿真，但尚未接入。接入高精度后端将提升规则的可信度，但也会显著增加单次评测时间和基础设施复杂度。
