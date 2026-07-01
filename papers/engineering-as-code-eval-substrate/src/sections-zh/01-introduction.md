# 1. 引言

软件工程已经形成了一个清晰的 agent 进步循环：代码是文本原生、可版本控制、可执行、可测试的工件；issue、pull request 与测试套件把真实开发活动转化为可复现任务；HumanEval 和 SWE-bench 等评测又把这些任务变成模型、工具和训练方法共同优化的坐标系 [Chen et al., 2021; Jimenez et al., 2023]。代码 agent 的快速进步不仅来自模型变强，也来自一个稳定的 evaluation substrate：提交对象明确，正确性可执行，失败可定位，修复可迭代。

系统级工程设计尚未拥有类似底座。AI data center、通信站点、机械装配、能源系统、施工排程等任务同样充满确定性反馈：设备是否兼容，引用是否完整，功率是否超限，结构是否满足载荷，布局是否冲突，吊装路径是否可行，施工计划是否违反资源约束，全年运营是否满足 PUE、TCO 与 SLA。然而，这些反馈通常分散在 CAD/BIM 文件、PDF 规范、Excel 表格、商业 GUI、供应商手册、仿真软件和人工审查流程中。结果是，工程 agent 的评估常常退化为自然语言方案评审、孤立几何生成、文档问答，或昂贵且难复现的仿真 wrapper。

本文的核心主张可以压缩为一句话：**工程 agent 的关键瓶颈不是缺少更大的任务集，而是缺少可提交、可检查、可诊断、可修复、可优化的 executable evaluation substrate。** 换言之，engineering agents need executable evaluation substrates: submit-able representations, executable constraints, diagnosable repair loops, and optimizable contextual knowledge. 为了让这一主张可审稿、可复现、可证伪，本文不引入额外宏大 framing，而收窄为三条 evaluative claims：

1. **Representation claim**：在系统级工程任务中，文本原生、可 diff、可检查的工程状态比自然语言方案、GUI 状态或孤立工具调用更容易形成稳定 repair loop。
2. **Constraint claim**：可执行、可定位的 critic 能显著降低 pseudo-correctness，并提高 repair 后 pass rate；收益来自约束可执行覆盖率和诊断粒度，而不只是模型知道更多规则。
3. **Knowledge claim**：当设备曲线、气候、电价、成本和施工风险被转化为可优化模型时，评估可以从静态合规推进到 Pareto frontier probe；该 claim 是前沿 case study，而不是本文唯一主结果。

我们提出 Engineering as Code (EaC) 作为这种底座。EaC 将工程状态表示为文本原生、可版本控制的设计工件；将工程正确性转化为分层可执行 critic；将失败反馈组织成 agent 可消费的诊断；并将设备、气候、电价、成本、施工和运营知识纳入可计算模型，使评估不只判断合规，还能度量设计上限。与只暴露工具接口不同，EaC 的目标是定义 agent 提交什么、系统如何判定它是否正确、错误如何被定位、知识如何进入优化循环。

本文用三重鸿沟解释为什么这样的 substrate 必要。**表征鸿沟**使工程任务难以变成稳定提交对象；**约束鸿沟**使自然语言规范无法阻止 pseudo-correctness；**知识鸿沟**使 agent 即使满足保守规则，也难以触及前沿工程实践中的跨层优化上限。三者并非松散并列的问题清单，而对应 evaluation substrate 的三个设计要求：状态必须可表征，正确性必须可执行，知识必须可优化。

我们以 AI Data Center Design 作为 reference domain，但 EaC 的适用边界并不限定在数据中心。AIDC 有用，是因为它把多类系统级工程困难压缩到同一场景中：设备选型、供配电、冷却、储能、光伏、机柜布局、施工可建性、EPC 排程、气候、电价、负载和生命周期成本。这使它成为测试 representation、executable constraints 和 optimizable knowledge 的压力测试域。相同的 substrate pattern 可以通过替换对象词汇、约束库和领域模型迁移到其他工程领域：通信站点将机柜和冷机替换为天线、RRU、机柜、电源和站址布局约束；机械装配将设备连接替换为零件、配合、公差、载荷和干涉检查；能源系统将数据中心负载替换为发电设备、储能、并网、调度策略和可靠性约束。SD-HWE-Bench 则提供当前实现：ADL 工程声明、DTS 分层 critic、canonical lineage 任务抽取、actor 隔离运行和可归档评分结果。

本文按 NeurIPS Evaluations & Datasets Track 的口径组织贡献：evaluation 本身是研究对象，而非模型论文的附属实验；该 track 对可执行 artifact、数据/代码托管、文档和机器可读元数据有明确要求 [NeurIPS E&D, 2026]。我们关心的是：当系统级工程任务被组织为不同的提交对象、约束反馈和知识条件时，agent 的成功率、失败模式、修复曲线和优化上限会如何变化。因此，本文的实验不以“某个模型最好”为主线，而以 evaluation design 如何改变可支持的科学结论为主线。投稿版第 4-6 章必须采用 results-first 叙事：每章只保留一个研究问题，随后给出真实表格或主图，再解释结果如何支持或削弱对应 claim；完整 protocol 与 gate 放入附录。

本文贡献如下：

1. 提出 Engineering as Code 作为面向 engineering agents 的 executable evaluation substrate，区别于单纯的工程设计表示或工具接口。
2. 将 representation、constraint、knowledge gaps 重新表述为 substrate 的三个必要能力：可闭环表征、可执行约束、可优化知识。
3. 给出基于 SD-HWE-Bench 与 AI Data Center Design 的三组受控 evaluation-design 实验，分别对应 representation、constraint 与 knowledge claims。当前中文稿保留结果表模板，但投稿版必须由隔离运行的 run artifacts 自动填充结果；任何未完成实验只能降级为 ablation、probe 或 future work，不能伪装成完整结果。
4. 给出 reviewer-facing artifact contract：入口 README、安装与 smoke test、30 分钟复现路径、完整复现实验矩阵、task/data card、scorer determinism、actor isolation、license、匿名化托管与 Croissant/RAI metadata 要求。
