# 附录 A：实验与 Artifact Gate

本附录用于把论文中的 `【TBD】` 占位符替换为可复现结果。任何进入正文的数字，都必须能回溯到任务、模型、条件、run manifest、score artifact 和生成脚本。

## A.1 通用复现要求

- 运行必须启用 actor isolation；正式结果不得来自可读取 reference solution 的工作区。
- 每个实验条件记录 task id、model/actor spec、context mode、repair 设置、随机种子或 attempt id、timeout、sandbox 设置和 commit hash。
- 每个样本归档 prompt、actor output、trajectory、workspace、score artifacts、manifest 和最终判定。
- 结果表由脚本从 artifacts 生成；正文不得手工填写无法重建的数字。
- 所有 `【TBD】` 在投稿版前必须替换，或明确标注为后续工作而不是实验结果。

## A.2 可闭环表征实验 Gate

- 选择 3-5 个等价工程需求，覆盖低耦合布置、跨专业约束、AIDC 设计-调度和 EPC 排程。
- 为 NL-only、CUA/GUI、MCP/Tool、Parametric、ADL/EaC 五类路径定义最小可行操作协议。
- 构造 Gen-only、Gen + Verify、Gen + Cross-domain、Gen + Buildable、Full closed-loop 等闭环能力条件。
- 记录任务形式化成本、提交确定性、反馈延迟、错误定位粒度、repair 成功率、评分覆盖度、可迁移成本和交接成本。
- 产出表征路径闭环能力矩阵、闭环覆盖率-质量曲线和跨专业冲突 case study。

## A.3 可执行约束实验 Gate

- 至少运行 NL-only、Docs-only、Full executable 三种条件；Partial executable 可作为扩展 ablation。
- 按约束族或评分层控制可见性和反馈可见性，最终评分始终使用完整 critic。
- 构造 No diagnostic、Coarse diagnostic、Attributed diagnostic、Localized diagnostic 四种诊断粒度条件，或在正式稿中说明为何只报告其中一部分。
- 定义 pseudo-correctness 人工标注协议，并统计标注一致性。
- 统计 pass@1、repair 后 pass rate、omission density、不可见约束真实违规率、Top omission constraints 和 repair saturation curve。
- 对低耦合、中耦合、高耦合任务分别报告结果，避免用总体平均值掩盖 failure mode。

## A.4 可优化知识实验 Gate

- 整理 AIDC 候选设备库、效率曲线、报价、维保成本、交期和故障/风险参数；不可公开参数必须替换为合成参数。
- 固定地点气候、电价、水价、负载曲线和 SLA 场景。
- 构造 Static Compliance、Static + Cost、Static + Curves、Dynamic Knowledge、Oracle Optimizer 五类知识条件。
- 跑 Fixed Design、Equipment-only、Schedule-only、Joint DTCO 四种优化权限设置，或在正文中明确缩小为 frontier probe。
- 对所有条件使用完整动态评估器离线重评。
- 绘制 CAPEX-TCO、CAPEX-SLA risk、OPEX-PUE 或 energy-SLA Pareto frontier。
- 记录 decision shift：设备组合、储能容量、冷却策略、调度策略和施工风险响应的变化。

## A.5 投稿前文本 Gate

- 引言贡献必须声明本文主贡献是 evaluation substrate，而不是单纯 dataset size。
- 第 3 章必须包含 evaluative claims、assumptions 和 artifact contract。
- 第 4-6 章所有趋势性分析必须与实际结果一致；若不一致，优先保留结果并改写分析。
- 讨论章必须保留任务规模、IC/EDA favorable case、repair 饱和和 AIDC 外部效度四类防守文本。
- 局限性必须说明任务覆盖、ADL 成熟度、pseudo-correctness 标注、AIDC probe、非训练算法贡献、匿名化和可复现性边界。
