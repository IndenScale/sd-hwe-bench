# 附录 B：AIDC 长程任务中的诊断契约失败

本附录记录 P0 可执行约束实验中的一个 artifact 发现：AIDC detailed-design 与 EPC 长程任务的一部分失败，并不能干净地解释为模型缺少工程能力，而是暴露了 executable substrate 自身的 **diagnostic contract** 不足。这些样本仍进入第 5 章 frozen baseline 的主表，因为它们是真实运行结果；但对失败原因的解释必须单独展开，不能把所有 budget-exhausted 样本都归因于模型能力不足。

## B.1 观察到的失败模式

在 `aidc-60mw-002` 和 `aidc-60mw-003` 的短预算运行中，Agent 多次生成了语义上接近正确的施工或 CPML 文件，但字段命名与当前 critic/parser 的机器契约不一致。例如：

| 文件 | Agent 常见写法 | Parser / Critic 期望写法 | 原始诊断 |
| ---- | -------------- | ------------------------ | -------- |
| `schedule.yaml` | `prerequisites` | `predecessors` | 未指出字段别名，依赖被静默忽略 |
| `schedule.yaml` | `resource_requirements` | `resources` | 未指出字段别名，资源请求被静默忽略 |
| `contingency-policy.yaml` | `contingency_policy` | `decisions` | `Contingency policy is empty` |
| `contingency-policy.yaml` | `type` | `decision` | 未指出字段别名 |
| `construction/hoisting-plan.yaml` | `hoisting_plan` | `hoists` | `missing hoisting-plan entry` |
| `construction/equipment-rental.yaml` | `equipment_rental` | `equipment` | `missing main-crane entry` |
| `construction/vdc-workface.yaml` | `vdc_workfaces` | `workfaces` | `need at least 2 workfaces, found 0` |

这些失败的共同点是：Agent 并非完全没有产出对应工程内容，而是产出的 YAML 没有满足 parser 的精确字段契约。原始 critic 把这类问题报告为空策略、缺失条目或任务级失败，却没有暴露“期望字段、实际字段、修复建议”。因此，repair loop 没有收到足够可消费的 compiler feedback。

## B.2 为什么需要单独解释

正文第 5 章检验的是：在 AIDC 长程压力测试中，可执行约束和可定位诊断是否改变 Agent 的 failure mode。上述样本进入主结果表，但它们同时混入了工具链契约缺陷：

- Parser 对字段别名不宽容，同时没有把别名错误提升为字段级诊断。
- 部分字段被静默忽略，导致评分结果看似合理但语义失真，例如 EPC 排程依赖被忽略后得到异常短的 makespan。
- Localized diagnostic 在这些 case 中退化为 task-level summary，无法告诉 Agent 应把 `contingency_policy` 改为 `decisions`。

因此，AIDC 这些 run 可以作为 frozen baseline 报告，但不应作为“模型不能完成长程工程任务”的干净证据。它们更适合作为 artifact lesson：可执行约束不仅需要 critic，还需要 **compiler-grade schema diagnostics**。换言之，主表报告的是当前 substrate 下的真实行为；本附录解释其中哪些失败属于 diagnostic-contract bottleneck。

## B.3 修复后的契约

修复后的 critic 不放宽评分标准，也不把错误别名自动视为通过；它只把原先模糊的任务级失败改写成可修复的 schema-contract diagnostic。例如：

```text
schedule.yaml: expected field 'predecessors'; found 'prerequisites'
schedule.yaml: expected field 'resources'; found 'resource_requirements'
contingency-policy.yaml: expected root key 'decisions' as a list; found 'contingency_policy'
construction/hoisting-plan.yaml: expected root key 'hoists' as a list; found 'hoisting_plan'
construction/equipment-rental.yaml: expected root key 'equipment' as a list; found 'equipment_rental'
construction/vdc-workface.yaml: expected root key 'workfaces' as a list; found 'vdc_workfaces'
```

这使后续重跑可以真正测试 Agent 是否能利用字段级诊断完成 repair，而不是测试它是否能猜中未文档化的 YAML 根键。

## B.4 对本文主张的影响

这个发现不削弱正文主张，反而限定了主张的适用条件：

> Executable constraints improve repair only when diagnostics expose the contract that the Agent must satisfy.

换言之，EaC substrate 的核心不只是“有检查器”，还包括四个连续环节：

1. 可提交的工程表示；
2. 可执行的约束；
3. 可定位、可归因、可消费的诊断；
4. 可以通过 repair loop 再提交的工作区。

AIDC schema-contract failure 说明，第三环缺失时，即使 critic 本身正确，Agent 也可能陷入重复失败。

## B.5 后续处理

本文对这类样本采用如下处理：

- 将原始 AIDC schema-contract failure 保留在第 5 章 frozen baseline 主表中，避免后验剔除真实失败。
- 在附录中报告它们作为 diagnostic-contract negative finding，防止把工具链契约不足误写成纯模型能力不足。
- 修复工具链后，用独立 run 目录重跑受影响的 AIDC executable 条件。
- 重跑结果单独标记为 post-fix rerun，不与修复前 P0 主表混合。
