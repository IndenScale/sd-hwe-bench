# 6. 实验三：地域化可优化知识

知识实验默认规则检查已经存在，进一步追问知识是否会改变设计选择和优化上限。研究问题只有一个：**在受控 AIDC probe 中，气候、电价、供应链和调度知识是否能暴露静态合规评估看不到的 design and dispatch margins？** 我们测试当公开气候数据、地域化水电价格、绿电/普通电结构、碳价负担和典型设备报价被转化为模型参数、目标函数和搜索空间后，agent 是否能从通用合规方案走向地域化方案，并进一步通过储能、蓄冷和协同调度释放 margin。

本实验在论文中的角色是 regional synthetic frontier probe，不承担唯一主结果。第 5 章的约束实验支撑“evaluation substrate 改变 failure attribution 和 repair dynamics”；本章进一步探索：当正确性已经可执行之后，受控地域化知识是否暴露静态合规评估看不到的设计与调度 margin。

投稿版应把本章写成 bounded AIDC probe：主文只放 margin decomposition 和一张 Pareto/frontier 图，完整数据生成规则和敏感性分析下沉到附录。若正式实验不能支持清晰 frontier shift，本章应降级为 ablation 或 future work，而不是声称完整工业数据中心优化能力。

## 6.1 主结果应回答的问题

“知识”这个词太宽。工程知识可以指规范条文、设备参数、施工经验、供应商报价、气候数据、电价曲线、招商补贴、园区政策、并网谈判条件，也可以指模型训练语料中的一般常识。本文关心的问题更窄：

**什么样的工程知识能够暴露设计与调度 margin？**

我们的回答是：能够进入设计变量、动态模型、目标函数、约束接口或搜索空间，并改变 Pareto frontier 的可优化工程知识。真实工程系统中，这类知识不应局限于地域化公开数据；它还应当接入准实时设备库、供应链数据库、能耗与气象数据库、运行遥测、采购结果和商业谈判结果。本文选择地域化公开知识作为实验切面，是出于学术评测的可复现性、匿名性和审稿可检查性，而不是把它定义为 EaC substrate 的能力边界。因此，本章的可复现实验只保留公开气候序列、地区水价、电价结构、绿电/普通电比例、碳价或碳税负担、典型设备价格与效率曲线，并把招商引资政策、财政补贴、个案谈判电价、非公开并网协议和项目特许条件放在真实部署扩展中讨论。本文的 claim 不是“合成数据能预测真实项目成本”，而是：**在受控的地域化合成 AIDC 场景中，气候、电价和供应链知识能够暴露静态合规评估看不到的设计与调度 margin。**

## 6.2 为什么选择 AI Data Center Design

AIDC 同时包含设备选型、冷却系统、供配电、储能、光伏、机柜布局、当地气候、分时电价、水价、绿电消纳、碳负担和运营调度。局部满足规则并不意味着全局最优。例如，更高 CAPEX 的冷却设备、蓄冷罐或储能系统可能允许更激进的调度策略，降低全年 OPEX 或 SLA 风险；当地湿球温度会改变 free cooling 和蓄冷价值；电价与绿电时段会改变电池充放电策略；碳价会改变夜间火电、白天绿电和储能/蓄冷之间的调度边界。

这些知识很难固化为简单 rule check。规则可以判断是否违反最低要求；知识实验关心的是，在相同可行域内，地域化情境是否改变目标景观，并推动 Pareto frontier 外移。实验的重点不是“哪个地区最适合建设 AIDC”，而是同一 evaluation substrate 能否复现地比较通用设计、地域化设计和地域化协同调度之间的 margin。

本章使用三组核心对照：

| 对照                                              | 要回答的问题                                                       | 可报告 margin          |
| ------------------------------------------------- | ------------------------------------------------------------------ | ---------------------- |
| Generic Design vs Regional Design                 | 同一通用设计在不同区域是否损失效率？                               | regionalization margin |
| Regional Design vs Regional Design + Dispatch     | 只做地域化选型/布局，和同时做运营调度，差多少？                    | coordination margin    |
| Static Compliance vs Dynamic Synthetic Evaluation | 只满足容量/冗余/间距规则，和基于气候、电价、负载时序优化，差多少？ | knowledge margin       |

## 6.3 知识条件

在同一 AIDC 设计-运营任务上设置四档条件。所有条件都使用同一套硬性可执行约束作为最终可行性闸门，差异只在地域化知识是否进入目标函数、模型参数和搜索空间。地域划分采用典型气候-电力-水价组合，而不是行政优惠政策：西北、华北、东部沿海、华南、中南。

| 条件                     | Agent 可用信息                                                                   | 评估方式                    | 目的                                      |
| ------------------------ | -------------------------------------------------------------------------------- | --------------------------- | ----------------------------------------- |
| Generic Baseline         | 统一设备库、统一 PUE 假设、统一冷却策略、统一电价，不针对区域优化                | 跨地域离线重评              | 测试一套通用设计在不同地域损失多少 margin |
| Climate-localized Design | 按气候区调整冷却方案、free cooling potential、冷机/液冷配置和温控策略            | 地域化气候仿真              | 测试气候知识是否改变冷却与 SLA margin     |
| Market-localized Design  | 加入地域化设备报价、施工成本、电力价格、绿电比例、碳价和交期风险                 | 地域化 LCC/TCO/PUE/SLA 评分 | 测试市场知识是否改变 CAPEX/OPEX 权衡      |
| Joint Design + Dispatch  | 设备选型、储能容量、蓄冷容量、冷却策略、温度设定点、负载迁移、储能充放电协同优化 | 时序仿真 + Pareto frontier  | 测试地域化协同调度是否进一步释放 margin   |

关键控制原则是：最终可行性约束不变。知识条件只改变可优化信息和评分目标，不改变工程底线。所有条件最终都用完整动态评估器离线重评，避免静态条件因为评分较弱而虚高。

五类 region archetypes 定义如下。它们不是行政区域覆盖声明，而是由公开气象序列、合成设备报价、区域电价模板和负载曲线生成的代表性场景：

| Region archetype | 代表气候/工程假设                           | 主要优化机会                          |
| ---------------- | ------------------------------------------- | ------------------------------------- |
| 西北             | 干冷、昼夜温差大、部分地区新能源丰富        | free cooling、储能、电价/弃风弃光响应 |
| 华北             | 冬冷夏热、供电与用地约束中等                | 季节性冷却策略、峰谷电价调度          |
| 东部沿海         | 高负载需求、高电价/高土地成本、湿热季节明显 | 高效冷却、空间密度、CAPEX/OPEX 权衡   |
| 华南             | 高温高湿、free cooling 弱                   | 液冷/高效冷机、水耗/SLA 风险控制      |
| 中南             | 夏热冬冷、季节差异明显                      | 混合冷却、季节调度、储能套利          |

## 6.4 数据生成规则与合成数据边界

本实验把数据分成三层，避免把不可公开的商业项目经验伪装成 benchmark truth：

| 数据层                                | 来源                                                              | 用途                                         |
| ------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------- |
| Public exogenous data                 | 气候、湿球温度、干球温度、太阳辐照、区域分时电价模板              | 生成地域时序环境                             |
| Semi-synthetic market data            | 设备价格、交期、维保成本、施工成本；由公开范围估计后加区域乘子    | 生成地域化 CAPEX/OPEX 和 supply-chain margin |
| Synthetic workload and design library | AI 负载曲线、机柜功率密度、冷却候选、储能候选、蓄冷候选、液冷比例 | 生成可控设计空间和调度空间                   |

本文不使用 synthetic market data 声称真实项目成本精度；它只用于测试 evaluation substrate 能否在受控、可复现假设下暴露 localized knowledge 解锁的设计 margin。所有合成参数都需要给出生成规则、区域乘子、扰动范围和敏感性分析。

## 6.5 主结果表与指标

本实验不以 pass rate 为主指标。pass/fail 只用于确保方案处于可行域内，真正的观测对象是 frontier 和目标权衡：

- **Feasibility rate**：满足硬性可执行约束的比例。
- **TCO**：生命周期总成本。
- **CAPEX / OPEX**：投资与运营成本拆分。
- **PUE / annual energy**：全年能耗和冷却效率。
- **SLA violation rate**：温控、供电、容量或服务水平违规率。
- **Water usage / water cost**：用水量与水费。
- **Carbon cost / green-power utilization**：普通电碳负担、绿电利用率、储能和蓄冷对碳成本的削减。
- **Storage / thermal-storage utilization**：电池充放电、蓄冷罐充放冷与负载窗口之间的关系。
- **Risk metrics**：极端天气、价格波动、供应延迟或设备故障下的风险。
- **Margin**：`(Baseline Cost - Optimized Cost) / Baseline Cost`。
- **Margin decomposition**：regionalization margin、supply-chain localization margin、coordination/dispatch margin。
- **Pareto dominance / dominance margin**：localized + coordinated knowledge 下 Pareto frontier 的外移程度。
- **Decision shift**：设备组合、储能容量、蓄冷容量、冷却策略、绿电/普通电调度策略是否发生可解释变化。

正式结果表使用如下模板。与第 5 章不同，本章在投稿版中可以作为 frontier probe；如果实验规模不足，主文只保留关键图和一张摘要表，完整矩阵进入附录。主结果不是绝对 TCO 精度，而是受控条件下的 margin decomposition。当前表格模式：**{{ data.eval_substrate.artifact.result_label }}**。{{ data.eval_substrate.artifact.result_note }}

| 条件 | TCO | PUE | SLA risk | CAPEX | OPEX | Margin vs Generic |
| ---- | --: | --: | -------: | ----: | ---: | ----------------: |

{% for row in data.eval_substrate.experiments.knowledge.knowledge_rows -%}
| {{ row.condition }} | {{ row.tco }} | {{ row.pue }} | {{ row.sla_risk }} | {{ row.capex }} | {{ row.opex }} | {{ row.margin_vs_generic }} |
{% endfor %}

区域分解结果使用如下模板：

| 区域 | Climate margin | Tariff margin | Supply-chain margin | Dispatch margin | Total margin |
| ---- | -------------: | ------------: | ------------------: | --------------: | -----------: |

{% for row in data.eval_substrate.experiments.knowledge.region_margin_rows -%}
| {{ row.region }} | {{ row.climate_margin }} | {{ row.tariff_margin }} | {{ row.supply_chain_margin }} | {{ row.dispatch_margin }} | {{ row.total_margin }} |
{% endfor %}

## 6.6 结果解释规则

本章必须防止过度宣称。Generic Baseline 若已经接近 Joint Design + Dispatch，应解释为当前可行域、设备库、电价/碳价或目标函数不够区分，而不是把小幅差异包装成前沿突破。Joint Design + Dispatch 若在同一可行域内产生更清晰的 TCO/PUE/SLA/carbon tradeoff，分析需要展示具体 margin decomposition：气候、区域电价、供应链报价和协同调度分别贡献了多少。只有 localized + coordinated knowledge 相对 design-only 条件产生非支配解集外移，才能支撑“知识价值来自跨层组合”的强结论。

如果实验只观察到小幅 frontier shift，也不必直接视为失败。它可能说明当前任务的可行域太窄、设备库区分度不足、模型搜索能力不足，或知识条件未覆盖真实决定性变量。这类归因正是 E&D 语境下有价值的 evaluation finding：它说明 benchmark 结论受哪些评估假设控制。因此，本章在全文中的地位应低于第 5 章，不承担本文唯一主贡献。

## 6.7 与 PDK 的类比

半导体行业之所以能进行快速 DTCO，是因为 PDK 把工艺能力、规则和模型传递给设计工具。许多系统级工程没有类似机制：设备厂商、材料供应商、施工单位、业主和运营方的知识被分散保存，难以被 agent 或优化器统一消费。

AIDC probe 的意义在于展示：如果缺少 PDK-like knowledge infrastructure，agent 只能在保守规则下做局部合规；如果情境化知识能进入 EaC substrate 的设计变量、动态模型和优化目标，agent 才可能进行跨设备、跨布局、跨运营策略和跨施工风险的协同设计。
