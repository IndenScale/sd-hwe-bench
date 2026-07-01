# 附录 A：实验待办清单

## A.1 可闭环表征实验

- 选择 3-5 个等价工程需求，覆盖低耦合布置、跨专业约束、AIDC 设计-调度和 EPC 排程。
- 为 NL-only、CUA/GUI、MCP/Tool、Parametric、ADL/EaC 五类路径定义最小可行操作协议。
- 构造 Gen-only、Gen + Verify、Gen + Cross-domain、Gen + Buildable、Full closed-loop 等闭环能力条件。
- 记录任务形式化成本、提交确定性、反馈延迟、错误定位粒度、repair 成功率、评分覆盖度、可迁移成本和交接成本。
- 产出表征路径闭环能力矩阵、闭环覆盖率-质量曲线和跨专业冲突 case study。

## A.2 可执行约束实验

- 构造 NL-only、Docs-only、Partial executable、Full executable 四种覆盖率条件。
- 按约束族或评分层控制可见性和反馈可见性，最终评分始终使用完整 critic。
- 构造 No diagnostic、Coarse diagnostic、Attributed diagnostic、Localized diagnostic 四种诊断粒度条件。
- 定义 pseudo-correctness 人工标注协议，并统计标注一致性。
- 统计 pass@1、repair 后 pass rate、omission density、不可见约束真实违规率、Top omission constraints 和 repair saturation curve。
- 对低耦合、中耦合、高耦合任务分别报告结果。

## A.3 可优化知识实验

- 整理 AIDC 候选设备库、效率曲线、报价、维保成本、交期和故障/风险参数。
- 固定地点气候、电价、水价、负载曲线和 SLA 场景。
- 构造 Static Compliance、Static + Cost、Static + Curves、Dynamic Knowledge、Oracle Optimizer 五类知识条件。
- 跑 Fixed Design、Equipment-only、Schedule-only、Joint DTCO 四种优化权限设置。
- 对所有条件使用完整动态评估器离线重评。
- 绘制 CAPEX-TCO、CAPEX-SLA risk、OPEX-PUE 或 energy-SLA Pareto frontier。
- 记录 decision shift：设备组合、储能容量、冷却策略、调度策略和施工风险响应的变化。
