# 5. 实验二：可执行约束

本实验是本文的主实验。研究问题只有一个：**把工程规则从自然语言和文档转化为可执行、可定位、可归因的 critic，是否会改变 pseudo-correctness、failure attribution 和 repair loop？** 核心不在于 agent 是否“知道”工程规则，而在于规则是否进入了可执行反馈系统。

本章报告当前已经冻结的 P0 AIDC diagnostic-contract rerun。该 run 不是完整投稿矩阵：它只覆盖 1 个模型、2 个 AIDC 长程任务和 2 个可执行反馈条件；NL-only、Docs-only、表征实验和知识实验仍需后续补齐。因此，本章的实证主张被刻意收窄为：在 AIDC detailed-design 与 EPC 排程压力测试中，可执行 repair loop 是否能把首轮失败转化为可评分通过样本，并降低遗漏密度。

## 5.1 主结果应回答的问题

物理工程评估中的很多失败并非源于模型完全不知道规则，而是因为规则停留在自然语言、规范文档、经验审查或隐式流程中，没有变成系统可判定的反馈。自然语言规范可以表达“应当满足什么”，但不能稳定回答：

- 本次任务到底涉及哪些约束？
- 提交物是否真实满足这些约束？
- 若不满足，错误发生在哪个对象、字段、关系或约束层？

因此，完整实验不只比较 NL-only、Docs-only 和 Executable 三个离散条件，还拆解两个正交变量：约束可执行覆盖率，以及诊断信息粒度。当前 frozen run 聚焦其中一条最小可复现切片：`executable` 与 `partial-executable-l3-muted`。前者向 agent 暴露完整可执行诊断，后者静默一部分 L3 反馈，但最终评分仍使用完整约束集合。这个切片不能替代完整矩阵，却能检验一个关键机制：当 agent 收到可执行诊断后，失败是转化为修复、预算耗尽，还是暴露出诊断契约本身的问题。

## 5.2 轴 A：约束可执行覆盖率

约束可执行程度应作为连续变量处理，不能压缩成二元变量：

| 条件               | Agent 可见内容                       | 可执行检查   | Repair 反馈 | 目的                               |
| ------------------ | ------------------------------------ | ------------ | ----------- | ---------------------------------- |
| NL-only            | 任务描述中的自然语言约束             | 完整离线评分 | 无          | 测试自然语言要求是否足够           |
| Docs-only          | 任务描述 + 规范文档                  | 完整离线评分 | 无          | 测试大型规范是否会被正确提取和落实 |
| Partial executable | 部分约束进入提示词或 repair 反馈     | 完整离线评分 | 部分诊断    | 测试可执行反馈覆盖率与遗漏率关系   |
| Full executable    | 所有适用约束进入提示词或 repair 反馈 | 完整离线评分 | 完整诊断    | 测试完整可执行闭环的收敛能力       |

关键控制原则是：最终评分始终使用完整约束集合。NL-only 和 Docs-only 条件不降低工程正确性标准；它们只限制 agent 在生成阶段能看到和消费的反馈。这样，实验测量的是 evaluation environment 的差异，避免把评分器宽松程度混入对比。

当前 P0 矩阵优先覆盖 hard/coupled 任务，包括跨专业任务、涌现约束任务、AIDC detailed-design 和 EPC 排程任务。正式投稿版可扩展到更多模型、更多 pass 和 repair ablation；但主结论应先来自这组可解释、可归因的高耦合任务。

## 5.3 轴 B：诊断信息粒度

在相同 critic 和相同错误集合下，控制反馈给 agent 的 diagnostic 粒度：

| 条件                  | 反馈内容                                       | 目的                                   |
| --------------------- | ---------------------------------------------- | -------------------------------------- |
| No diagnostic         | 只告诉 failed                                  | 测试无定位反馈下 repair 是否退化为猜测 |
| Coarse diagnostic     | 自然语言摘要，不含精确对象/字段                | 测试普通审查意见的效果                 |
| Attributed diagnostic | 给出约束族、对象 id 和失败原因                 | 测试归因信息的作用                     |
| Localized diagnostic  | 给出文件、字段、对象、期望值、实际值和修复建议 | 测试可定位诊断的上限                   |

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

## 5.5 主结果表与主图

本章表格由 run artifacts 自动生成。当前数据模式：**{{ data.eval_substrate.artifact.result_label }}**。{{ data.eval_substrate.artifact.result_note }} 本次冻结数据包含 12 条有效 attempt，另有 1 条 `actor_error` artifact 因 provider socket 断开被保留但不计入 complete attempt。运行目录为 `{{ data.eval_substrate.artifact.assumptions.run_dir }}`。

| 条件 | Pass@1 | Repair 后 Pass | Pseudo-correctness | Omission Density | Median Repair Rounds | Top Failed Layer |
| ---- | -----: | -------------: | -----------------: | ---------------: | -------------------: | ---------------- |

{% for row in data.eval_substrate.experiments.constraint.summary_rows -%}
| {{ row.condition }} | {{ row.pass_at_1 }} | {{ row.pass_after_repair }} | {{ row.pseudo_correctness }} | {{ row.omission_density }} | {{ row.median_repair_rounds }} | {{ row.top_failed_layer }} |
{% endfor %}

这张表给出三个直接观察。

第一，两个条件的 `Pass@1` 均为 0%。这说明 AIDC detailed-design 与 EPC 排程不是单轮 YAML 补全任务；即使模型生成了结构完整、工程语气合理的提交，首轮也会在 L4/L5 的动态排程、热性能、可建性或 schema contract 上失败。这个结果符合本文对高耦合工程任务的预期：自然语言“看起来完整”不能替代可执行正确性。

第二，repair loop 显著改变了结果。完整可执行反馈条件从 0% 提升到 50%，部分 L3 反馈静默条件从 0% 提升到 33%。换言之，critic 不只是事后打分器；它成为 agent 可以消费的工程编译器反馈。即便没有通过的样本，omission density 也被压低到 0.19 和 0.31，说明提交在 repair 过程中逐步接近可执行约束。

第三，完整反馈优于部分反馈，但差距不是压倒性的。`partial-executable-l3-muted` 仍能达到 33% 的 repair 后通过率，说明一部分错误可以由剩余层级诊断间接修复；但它的 omission density 更高，预算耗尽更多，说明静默约束会留下更长的修复尾部。本文据此不声称“某一层反馈缺失会立即崩溃”，而声称“约束反馈覆盖率改变遗漏密度和预算耗尽概率”。

按提交预算观察，当前 frozen run 的 repair saturation 如下：

| 条件 | 提交预算前缀 | Pass Rate | Omission Density | Budget Exhausted | Attempts |
| ---- | -----------: | --------: | ---------------: | ---------------: | -------: |
{% for row in data.eval_substrate.experiments.constraint.submission_budget_rows -%}
| {{ row.condition }} | {{ row.submission_budget }} | {{ row.pass_rate }} | {{ row.omission_density }} | {{ row.budget_exhausted }} | {{ row.attempts }} |
{% endfor %}

从 budget=1 到 budget=5 的变化最关键：完整 executable 条件的 omission density 从 0.76 降到 0.19，partial 条件从 0.93 降到 0.31。更长的 20/50/100 行在当前 run 中是同一短预算轨迹的前缀视图，而不是独立长预算实验；因此它们只能说明“6 次提交预算内是否已经饱和”，不能作为 AIDC 长程搜索上限。

分层结果还应按任务复杂度报告：

| 任务类型               |  规模 | 耦合复杂度 | NL/Docs 预期失败           | Executable 预期收益    |
| ---------------------- | ----: | ---------: | -------------------------- | ---------------------- |
| 简单布置/连接          | 低-中 |         低 | 偶发字段遗漏               | 稳定性和防回归         |
| 大量对象但弱耦合       |    高 |      低-中 | 批量遗漏和引用漂移         | 降低偶发遗漏           |
| 跨文件/跨专业约束      |    中 |      中-高 | 本专业通过但跨专业失败     | 层级归因和局部修复     |
| 选型-布置-调度联合优化 | 中-高 |         高 | 动态约束与目标遗漏         | Repair loop 和目标反馈 |
| 设计-施工联合排程      | 中-高 |         高 | 可建性、资源和天气窗口遗漏 | L4/L5 诊断与排程修复   |

投稿版主文还应包含两张图：第一，repair curve，以 repair round 为横轴、pass rate 或 remaining violations 为纵轴；第二，violation layer distribution，比较不同反馈条件在 L0-L6 的失败分布。若篇幅紧，pseudo-correctness examples table 可以替代部分分层表格进入主文，完整表格放附录。

## 5.6 失败轨迹：从模型失败到诊断契约失败

最有解释力的结果来自未通过样本的 repair trajectory。`aidc-60mw-003` 的 EPC 排程样本多次生成了包含施工活动、资源计划和应急预案的交付物，但反复卡在 `Contingency policy is empty` 或 `CPML parse error`。轨迹显示，agent 并非没有意识到需要应急预案；它在 `policies`、`contingency`、`contingency_policies`、`contingency_policy`、`decisions` 以及是否嵌入 `schedule.yaml` 之间来回切换。真实 parser 期望的是 `contingency-policy.yaml` 根键 `decisions`，每条包含 `activity_id`、`decision` 和 `params`。当 diagnostic 只报告“empty”而没有稳定暴露字段契约时，repair loop 会退化为 schema guessing。

`aidc-60mw-002` 的 detailed-design 样本也出现类似现象。失败轨迹围绕 `hoisting-plan.yaml` 的 `hoists` 根键、`equipment_id` 与 facility `id` 的匹配、`equipment-rental.yaml` 的 `equipment` 列表和 `type: main-crane` 条目反复摆动。Agent 生成了吊装方案和租赁计划，但没有稳定命中 critic 的机器契约；部分 thermal 诊断还出现了不可操作的 `message: "{"`。这类失败不应被简单解释为“模型没有工程知识”，更准确地说，是 executable substrate 已经发现了错误，但 diagnostic contract 尚未达到 compiler-grade。

因此，本实验支持的主张有一个重要限定：可执行约束的收益不只来自“有 critic”，还来自 critic 是否能把失败表达成 agent 可消费的字段级契约。没有这个契约，repair loop 仍然比无反馈更可观察，但会出现命名振荡和预算耗尽。

## 5.7 结果解释规则

本实验要检验的是约束可执行性和诊断粒度是否改变 failure mode，而不是简单证明 Full executable 条件分数最高。NL-only 条件若产生文本完整、工程语气专业、交付物结构合理但 critic 失败的提交，应归类为 pseudo-correctness，并进一步标注失败层和遗漏约束。Docs-only 条件若降低显性规则遗漏但仍在长文档检索、跨文件落实和多约束组合处失败，应解释为“规范可见”与“约束可执行”之间的差距。Full executable 条件若提高 repair 后 pass rate，则必须展示诊断如何被消费；若没有提高，则应检查诊断粒度、上下文窗口、actor 行为或任务饱和，而不是直接归因于模型能力。

如果低耦合任务在 executable 条件下快速饱和，这应被视为 substrate 的诊断信号：该任务的主要困难来自规则可见性和局部修复，而非深层工程优化。真正需要进一步研究的失败会出现在跨专业耦合、隐藏约束、长程优化和不完备知识条件下。

## 5.8 本实验支撑的结论

本实验要支撑的结论是：物理工程任务中的真实性能由模型与可执行约束环境共同决定，不能只看模型本身。自然语言规范可以表达要求，但不能充分构成评估；可执行约束把“看起来正确”转化为“可以被证明正确或定位错误”；诊断粒度决定 repair 的效率与稳定性。

当前 frozen run 足以支持一个收窄但可提交的结论：在 AIDC 长程压力测试中，完整可执行反馈把 repair 后通过率提升到 50%，并将遗漏密度压到 0.19；部分反馈仍能修复一部分样本，但遗漏密度和预算耗尽更高。与此同时，失败轨迹暴露出 diagnostic contract 是 PEaC substrate 的一等对象。后续工具链修复应作为 post-fix sanity rerun 报告，而不应覆盖当前 frozen baseline。
