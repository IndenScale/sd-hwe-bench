# 5. 实验二：可执行约束

本实验是本文的主实验。它验证自然语言规范、文档规范和可执行约束之间的差异。核心问题不在于 agent 是否“知道”工程规则，而在于规则是否进入了可执行、可定位、可归因的反馈系统，从而阻止 pseudo-correctness 并支持 repair loop。

## 5.1 第一性问题

工程 agent 的很多失败并非源于模型完全不知道规则，而是因为规则停留在自然语言、规范文档、经验审查或隐式流程中，没有变成系统可判定的反馈。自然语言规范可以表达“应当满足什么”，但不能稳定回答：

- 本次任务到底涉及哪些约束？
- 提交物是否真实满足这些约束？
- 若不满足，错误发生在哪个对象、字段、关系或约束层？

因此，本实验不只比较 NL-only、Docs-only 和 Executable 三个离散条件，还拆解两个正交变量：约束可执行覆盖率，以及诊断信息粒度。当前代码路径已经支持 `run-repair --context-mode nl-only|docs-only|full`，并通过批量矩阵组织 P0 约束鸿沟实验。正式结果将由隔离 actor workspace、评分 artifacts 和 run manifest 重建。

## 5.2 轴 A：约束可执行覆盖率

约束可执行程度应作为连续变量处理，不能压缩成二元变量：

| 条件 | Agent 可见内容 | 可执行检查 | Repair 反馈 | 目的 |
|---|---|---|---|---|
| NL-only | 任务描述中的自然语言约束 | 完整离线评分 | 无 | 测试自然语言要求是否足够 |
| Docs-only | 任务描述 + 规范文档 | 完整离线评分 | 无 | 测试大型规范是否会被正确提取和落实 |
| Partial executable | 部分约束进入提示词或 repair 反馈 | 完整离线评分 | 部分诊断 | 测试可执行反馈覆盖率与遗漏率关系 |
| Full executable | 所有适用约束进入提示词或 repair 反馈 | 完整离线评分 | 完整诊断 | 测试完整可执行闭环的收敛能力 |

关键控制原则是：最终评分始终使用完整约束集合。NL-only 和 Docs-only 条件不降低工程正确性标准；它们只限制 agent 在生成阶段能看到和消费的反馈。这样，实验测量的是 evaluation environment 的差异，避免把评分器宽松程度混入对比。

当前 P0 矩阵优先覆盖 hard/coupled 任务，包括跨专业任务、涌现约束任务、AIDC detailed-design 和 EPC 排程任务。正式投稿版可扩展到更多模型、更多 pass 和 repair ablation；但主结论应先来自这组可解释、可归因的高耦合任务。

## 5.3 轴 B：诊断信息粒度

在相同 critic 和相同错误集合下，控制反馈给 agent 的 diagnostic 粒度：

| 条件 | 反馈内容 | 目的 |
|---|---|---|
| No diagnostic | 只告诉 failed | 测试无定位反馈下 repair 是否退化为猜测 |
| Coarse diagnostic | 自然语言摘要，不含精确对象/字段 | 测试普通审查意见的效果 |
| Attributed diagnostic | 给出约束族、对象 id 和失败原因 | 测试归因信息的作用 |
| Localized diagnostic | 给出文件、字段、对象、期望值、实际值和修复建议 | 测试可定位诊断的上限 |

同样是发现错误，“设计不满足电气约束”和“`instances/pdus/PDU-C.yaml` 的 `phase` 字段缺失或不满足三相均衡规则”对 agent 的修复效果完全不同。可执行约束的收益不仅来自发现错误，还来自错误能否被定位、归因和消费。

## 5.4 Pseudo-correctness 与遗漏密度

本实验定义两个核心观测量：

```text
Pseudo-Correctness Rate =
  verbally or structurally plausible submissions that fail executable critics
  / all plausible submissions
```

```text
Omission Density =
  missed required constraints / total applicable constraints
```

Pseudo-correctness 需要人工标注协议辅助定义，因为“看起来合理”包含一定主观性。但最终失败判定必须来自完整 critic。遗漏密度则按约束族和评分层统计：消防、防雷、结构、日照、接地、维护空间、接口、电源、热、施工；L1/L2 引用错误、L3 静态约束、L4 动态/调度、L5 几何/可建性。

## 5.5 结果表占位

正式结果表至少包含 pass、pseudo-correctness、omission 和 repair 四类信息：

| 条件 | Pass@1 | Repair 后 Pass | Pseudo-correctness | Omission Density | Median Repair Rounds | Top Failed Layer |
|---|---:|---:|---:|---:|---:|---|
| NL-only | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 |
| Docs-only | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 |
| Partial executable | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 |
| Full executable | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 | 【TBD】 |

分层结果还应按任务复杂度报告：

| 任务类型 | 规模 | 耦合复杂度 | NL/Docs 预期失败 | Executable 预期收益 |
|---|---:|---:|---|---|
| 简单布置/连接 | 低-中 | 低 | 偶发字段遗漏 | 稳定性和防回归 |
| 大量对象但弱耦合 | 高 | 低-中 | 批量遗漏和引用漂移 | 降低偶发遗漏 |
| 跨文件/跨专业约束 | 中 | 中-高 | 本专业通过但跨专业失败 | 层级归因和局部修复 |
| 选型-布置-调度联合优化 | 中-高 | 高 | 动态约束与目标遗漏 | Repair loop 和目标反馈 |
| 设计-施工联合排程 | 中-高 | 高 | 可建性、资源和天气窗口遗漏 | L4/L5 诊断与排程修复 |

## 5.6 趋势性分析占位

预期趋势是：NL-only 条件会产生较高比例的 pseudo-correctness，表现为文本完整、工程语气专业、交付物结构合理，但在引用完整性、跨专业约束、动态调度或可建性检查下失败。Docs-only 条件预计能降低显性规则遗漏，但仍会在长文档检索、跨文件落实和多约束组合处失败。Full executable 条件预计会提高 repair 后 pass rate，并把失败集中到更高层的动态优化、几何/施工可建性和知识更新问题上。

如果低耦合任务在 executable 条件下快速饱和，这应被视为 substrate 的诊断信号：该任务的主要困难来自规则可见性和局部修复，而非深层工程优化。真正需要进一步研究的失败会出现在跨专业耦合、隐藏约束、长程优化和不完备知识条件下。

## 5.7 本实验支撑的结论

本实验要支撑的结论是：工程 agent 的真实性能由模型与可执行约束环境共同决定，不能只看模型本身。自然语言规范可以表达要求，但不能充分构成评估；可执行约束把“看起来正确”转化为“可以被证明正确或定位错误”；诊断粒度决定 repair 的效率与稳定性。
