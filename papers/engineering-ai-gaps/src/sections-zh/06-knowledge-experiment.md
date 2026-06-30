# 6. 实验三：知识鸿沟

知识鸿沟实验关注的不是能否通过规则检查，而是知识是否改变优化上限。我们以 AIDC 设计-调度联合优化作为 probe。

## 6.1 为什么选择 AIDC

AIDC 同时包含设备选型、冷却系统、供配电、储能、光伏、机柜布局、当地气候、分时电价、施工约束和运营调度。局部满足规则并不意味着全局最优。例如，更高 CAPEX 的冷却设备或储能系统可能允许更激进的调度策略，降低全年 OPEX 或 SLA 风险；当地湿球温度会改变 free cooling 潜力；电价结构会改变储能容量与充放电策略；设备供应商曲线会改变 PUE/TCO 最优点。

这些知识很难固化为简单 rule check。规则可以判断“是否违反最低要求”，但知识鸿沟关心的是“是否能发现更高性能边界”。

## 6.2 实验设置

设计四种优化权限：

| 设置 | 可优化变量 | 知识范围 | 观察对象 |
|---|---|---|---|
| Fixed Design | 设备和布局固定，只优化调度 | 低 | 基线 PUE/TCO/SLA |
| Equipment-only | 可优化冷机、储能、变压器、光伏 | 中 | CAPEX/OPEX tradeoff |
| Schedule-only | 设备固定，可优化运营策略 | 中 | 峰谷套利与温控风险 |
| Joint DTCO | 设备选型 + 布局 + 调度联合优化 | 高 | Pareto frontier 外移 |

每个设置使用同一地点的气候数据、电价曲线、负载曲线和候选设备库。Agent 需要提交设计变量与调度策略，评估器计算全年 PUE、TCO、SLA violation、CAPEX、OPEX 和风险指标。

## 6.3 关键图表

最重要的图不是单一 pass rate，而是 Pareto frontier：

- x 轴：CAPEX 或初始投资。
- y 轴：TCO、annual OPEX 或 SLA risk。
- 曲线：Fixed Design、Equipment-only、Schedule-only、Joint DTCO。

如果 Joint DTCO 的 Pareto frontier 显著外移，就说明跨层知识进入优化循环会改变设计上限。这比“多一个规则检查”更接近前沿工程 AI 的真实价值。

## 6.4 与半导体 PDK 的类比

半导体行业之所以能进行快速 DTCO，是因为 PDK 把工艺能力、规则和模型传递给设计工具。许多系统级工程没有类似机制：设备厂商、材料供应商、施工单位、业主和运营方的知识被分散保存，难以被 Agent 或优化器统一消费。

AIDC probe 的意义在于展示：如果缺少 PDK-like knowledge infrastructure，Agent 只能在保守规则下做局部合规；如果情境化知识能进入可计算表示和优化模型，Agent 才可能进行跨设备、跨布局、跨运营策略的协同设计。

## 6.5 待补实验

本节需要补充：

- 候选设备库与供应商曲线。
- 地点气候与电价场景。
- 四种优化权限下的 PUE/TCO/SLA 结果。
- Pareto frontier 图。
- Agent 生成方案与参考优化器方案的差距分析。
