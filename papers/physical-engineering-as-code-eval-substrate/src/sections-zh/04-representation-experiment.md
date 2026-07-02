# 4. 实验一：可闭环表征

本实验验证不同工程表征路径能否支持严肃的物理工程自动化评估闭环。研究问题只有一个：**在同等工程意图下，什么样的表征接口能让 agent 的输出变成可提交、可检查、可诊断、可修复、可复现的评估对象？**

投稿版应在本章开头直接给出主结果表或主图，然后再解释表征差异造成的机制。当前中文稿中的表征表仍是 protocol / 待实验占位；正式数字必须由隔离 runs、score artifacts 和表格生成脚本重建。若某一表征路径无法完整复现，应在主文中明确降级为 case study 或 appendix protocol。

## 4.1 主结果应回答的问题

如果本文只说“工程缺少可计算表征”，很容易被参数化设计反驳。OpenSCAD、Revit family、Grasshopper、Dynamo、Excel 配置表和企业内部模板都已经能够用变量生成工程工件。因此本实验真正要问的是：

**参数化设计和工具调用是否已经足以成为 physical engineering evaluation 的 executable substrate？**

我们的假设是否定的。参数化设计解决了生成问题，MCP/Tool 接口增强了访问能力；但它们通常没有同时解决生成-验证、本专业-跨专业、设计-建造、当前项目-未来项目、个人知识-组织知识五重闭环。对于低耦合几何或单专业任务，这些路径可能表现很好；但在 AIDC 这类跨设备、跨布局、跨调度、跨施工的系统级任务上，缺失闭环能力会表现为 pseudo-correctness、repair 困难和不可复现评分。

CUA/GUI agent 不作为本实验主条件。通用 CUA 研究已经讨论视觉 agent 如何操作既有软件界面；本文关注的是操作完成后留下的工程表征是否能被归档、diff、重评和 repair。因此 CUA 在本文中作为相关工作与威胁讨论中的交互层，而不是 representation substrate 的主实验对照。

## 4.2 比较路径与控制变量

我们将同一工程需求组织为三类 artifact-bearing 表征路径，比较其闭环能力：

| 路径 | 典型形式 | 核心表征 | Agent 操作 | 预期特点 |
| --- | --- | --- | --- | --- |
| OpenSCAD code-only | code-like geometry | `.scad` 参数化源码 | 直接修改 OpenSCAD | 文本化、可 diff、可执行，是强参数化 baseline |
| OpenSCAD MCP / Tool | 外部 API、插件、工具调用 | 工具参数、设计状态、调用日志 | 调用建模工具并导出 `.scad` | 增强访问能力和审计性，但语义可能散落在工具状态中 |
| ADL + OpenSCAD | 声明式工程对象与关系 + OpenSCAD 生成器 | 对象、接口、约束、映射表、生成的 `.scad` | 修改工程声明文件 | 支持生成、验证、诊断和 repair 闭环 |

为了避免把“文本化程度”和“闭环能力”混在一起，实验加入两个控制。第一，同一 OpenSCAD 工件在“几何可运行”和“规格语义满足”两个层面分别评分。第二，同一 ADL + OpenSCAD 任务保留从语义对象到几何特征的映射表，比较诊断是否能定位到 object/field，而不仅是导出 mesh 的后处理失败。最终评分始终使用完整约束集合；不同条件只控制 agent 可见的表征接口和反馈能力。

## 4.3 闭环能力轴

实验把闭环能力作为独立变量，避免停留在工具名称对比：

| 条件               | 保留的能力                        | 目的                          |
| ------------------ | --------------------------------- | ----------------------------- |
| Gen-only           | 只保留生成能力                    | 测试“可计算但不闭环”的上限    |
| Gen + Verify       | 生成后用独立检查器评分            | 测试验证闭环的价值            |
| Gen + Cross-domain | 电气、热、结构、布局联合检查      | 测试跨专业闭环的价值          |
| Gen + Buildable    | 检查吊装、施工通道、排程和资源    | 测试设计-建造闭环的价值       |
| Gen + Transferable | 同一表征迁移到新项目或新设备库    | 测试当前-未来闭环的价值       |
| Gen + Documented   | 新人或 agent 无需作者解释即可修改 | 测试个人-组织闭环的价值       |
| Full closed-loop   | 五重闭环均保留                    | 测试完整 PEaC substrate 的上限 |

## 4.4 主结果表与证据要求

本实验不以 pass rate 为唯一指标，而关注 substrate 能力：

- **任务形式化成本**：从工程需求到可评测任务需要多少人工建模步骤。
- **提交确定性**：同一提交是否能稳定复现评分。
- **反馈延迟**：从提交到结构化错误反馈的时间。
- **错误可定位性**：错误能否定位到对象、字段、引用或规则。
- **repair 可行性**：agent 是否能基于反馈进行局部修复。
- **评分覆盖度**：是否覆盖语法、引用、工程约束、几何、仿真、交付物和可建造性。
- **跨专业冲突检出率**：本专业检查通过但跨专业联合检查失败的比例。
- **可迁移成本**：同一表征应用到新地点、新设备库或新规范所需调整量。
- **交接成本**：新成员或 agent 在没有原作者解释时复现和修改表征所需轮次。

投稿版的正式结果表必须放在本章前半部分，由脚本从 artifacts 生成，并至少对应一个可复现的 case study 或任务集合。读者应先看到不同表征路径在形式化成本、确定性、诊断和 repair 上的差异，再进入 protocol 细节。当前表格模式：**{{ data.eval_substrate.artifact.result_label }}**。{{ data.eval_substrate.artifact.result_note }}

| 表征路径 | 形式化成本 | 提交确定性 | 反馈延迟 | 定位粒度 | Repair 成功率 | 评分覆盖度 | 跨专业冲突检出 | 交接成本 |
| -------- | ---------: | ---------: | -------: | -------- | ------------: | ---------: | -------------: | -------: |

{% for row in data.eval_substrate.experiments.representation.summary_rows -%}
| {{ row.condition }} | {{ row.formalization_cost }} | {{ row.submission_determinism }} | {{ row.feedback_latency }} | {{ row.localization }} | {{ row.repair_success_rate }} | {{ row.scoring_coverage }} | {{ row.cross_domain_detection }} | {{ row.handoff_cost }} |
{% endfor %}

## 4.5 结果解释规则

本实验不得用“ADL 必然更好”作为预设结论。低耦合任务中，OpenSCAD code-only 与 ADL + OpenSCAD 的质量差距可能不显著，差异可能主要体现在可审计性、诊断粒度和交接成本；这不是反例，而是说明低耦合生成任务不需要完整 substrate。中高耦合任务中，如果 OpenSCAD code-only 或 MCP/Tool 出现跨文件引用遗漏、局部工具状态不可复现、或本专业正确但跨专业失败，分析必须回到具体 failed layer、对象和诊断记录。

正式分析将按任务复杂度分层报告，避免用单一平均值掩盖机制差异。真正能区分 evaluation substrate 的，不是“谁在一个简单任务上得分更高”，而是跨专业耦合、动态调度、施工可建性和知识迁移条件下，哪种表征能保留提交确定性、错误定位和局部 repair 能力。若结果与这一机制不一致，应优先修改论文解释，而不是选择性展示任务。

## 4.6 本实验支撑的结论

本实验要支撑的结论是：physical engineering evaluation 需要“可闭环的工程表征”，不能满足于“可计算的工程工件”。参数化设计解决生成问题，工具接口解决访问问题；PEaC substrate 的贡献在于把工程状态变成 agent 可提交、critic 可检查、错误可定位、知识可迁移、repair 可迭代的评估对象。CUA/GUI 可作为交互层提升操作效率，但不自动提供这些 substrate 性质。
