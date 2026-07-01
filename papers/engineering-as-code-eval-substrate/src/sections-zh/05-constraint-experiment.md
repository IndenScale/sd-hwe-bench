# 5. 实验二：可执行约束

本实验验证自然语言规范、文档规范和可执行约束之间的差异。核心问题不是 agent 是否“知道”工程规则，而是规则是否进入了可执行、可定位、可归因的反馈系统，从而阻止 pseudo-correctness 并支持 repair loop。

## 5.1 第一性问题

工程 agent 的很多失败不是因为模型完全不知道规则，而是因为规则停留在自然语言、规范文档、经验审查或隐式流程中，没有变成系统可判定的反馈。自然语言规范可以表达“应当满足什么”，但不能稳定回答：

- 本次任务到底涉及哪些约束？
- 提交物是否真实满足这些约束？
- 若不满足，错误发生在哪个对象、字段、关系或约束层？

因此，本实验不只比较 NL-only、Docs-only 和 Executable 三个离散条件，还拆解两个正交变量：约束可执行覆盖率，以及诊断信息粒度。

## 5.2 轴 A：约束可执行覆盖率

约束可执行程度应作为连续变量，而不是二元变量：

| 条件 | Agent 可见内容 | 可执行检查 | 目的 |
|---|---|---|---|
| NL-only | 任务描述中的自然语言约束 | 无 | 测试自然语言要求是否足够 |
| Docs-only | 任务描述 + 规范文档 | 无 | 测试大型规范是否会被正确提取和落实 |
| Partial executable | 部分约束进入提示词或 repair 反馈 | 完整评分，部分反馈 | 测试可执行反馈覆盖率与遗漏率关系 |
| Full executable | 所有适用约束进入提示词或 repair 反馈 | 完整评分，完整反馈 | 测试完整可执行闭环的收敛能力 |

Partial executable 条件可以通过三种方式构造。第一，随机对 agent 隐藏一部分约束，记录隐藏约束是否被遗漏。第二，按约束族控制可见性，例如电气、热、结构、布局、施工、调度、交付物。第三，按评分层控制反馈，例如只反馈 L0-L2、L0-L3、L0-L4 或 L0-L5 的诊断。无论哪种方式，最终评分始终使用完整约束集合。

核心指标包括 pass@1、repair 后 pass rate、pseudo-correctness rate、omission density、不可见约束真实违规率、constraint coverage 与 final quality 的关系曲线，以及 repair saturation curve。

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

## 5.5 任务分层

实验不能把结论简化成“任务越大，可执行约束越有用”。需要区分规模增长和复杂性增长：

| 任务类型 | 规模 | 耦合复杂度 | 预期现象 |
|---|---:|---:|---|
| 简单布置/连接 | 低-中 | 低 | NL 也可能高通过；executable 主要提升稳定性 |
| 大量对象但弱耦合 | 高 | 低-中 | executable 降低偶发遗漏和回归 |
| 跨文件/跨专业约束 | 中 | 中-高 | NL/docs 与 executable 开始分叉 |
| 选型-布置-调度联合优化 | 中-高 | 高 | executable 显著提升 pass、repair 和质量 |

低耦合饱和任务不是反例。它们说明当约束完备且反馈可消费时，agent 可以像软件工程中的开发者一样快速迭代修复。真正困难的任务会转移到跨专业耦合、动态优化和知识更新。

## 5.6 预期结论

本实验要支撑的结论是：工程 agent 的真实性能不是模型单独决定的，而是模型与可执行约束环境共同决定的。自然语言规范可以表达要求，但不能充分构成评估；可执行约束把“看起来正确”转化为“可以被证明正确或定位错误”；诊断粒度决定 repair 的效率与稳定性。
