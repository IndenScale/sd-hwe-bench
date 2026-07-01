# 1. 引言

软件工程已经形成了一个清晰的 agent 进步循环：代码是文本原生、可版本控制、可执行、可测试的工件；issue、pull request 与测试套件把真实开发活动转化为可复现任务；SWE-bench 等评测又把这些任务变成模型、工具和训练方法共同优化的坐标系。代码 agent 的快速进步不仅来自模型变强，也来自一个稳定的 evaluation substrate：提交对象明确，正确性可执行，失败可定位，修复可迭代。

系统级工程设计尚未拥有类似底座。AI data center、通信站点、机械装配、能源系统、施工排程等任务同样充满确定性反馈：设备是否兼容，引用是否完整，功率是否超限，结构是否满足载荷，布局是否冲突，吊装路径是否可行，施工计划是否违反资源约束，全年运营是否满足 PUE、TCO 与 SLA。然而，这些反馈通常分散在 CAD/BIM 文件、PDF 规范、Excel 表格、商业 GUI、供应商手册、仿真软件和人工审查流程中。结果是，工程 agent 的评估常常退化为自然语言方案评审、孤立几何生成、文档问答，或昂贵且难复现的仿真 wrapper。

本文的核心主张是：**engineering agents 不能只依赖更多任务；它们需要一种可提交、可检查、可诊断、可修复、可优化的 executable evaluation substrate。**

我们提出 Engineering as Code (EaC) 作为这种底座。EaC 将工程状态表示为文本原生、可版本控制的设计工件；将工程正确性转化为分层可执行 critic；将失败反馈组织成 agent 可消费的诊断；并将设备、气候、电价、成本、施工和运营知识纳入可计算模型，使评估不只判断合规，还能度量设计上限。与只暴露工具接口不同，EaC 的目标是定义 agent 提交什么、系统如何判定它是否正确、错误如何被定位、知识如何进入优化循环。

本文用三重鸿沟解释为什么这样的 substrate 必要。**表征鸿沟**使工程任务难以变成稳定提交对象；**约束鸿沟**使自然语言规范无法阻止 pseudo-correctness；**知识鸿沟**使 agent 即使满足保守规则，也难以触及前沿工程实践中的跨层优化上限。三者并非松散并列的问题清单，而对应 evaluation substrate 的三个设计要求：状态必须可表征，正确性必须可执行，知识必须可优化。

我们以 AI Data Center Design 作为 reference domain，但 EaC 的适用边界并不限定在数据中心。AIDC 有用，是因为它把多类系统级工程困难压缩到同一场景中：设备选型、供配电、冷却、储能、光伏、机柜布局、施工可建性、EPC 排程、气候、电价、负载和生命周期成本。这使它成为测试 representation、executable constraints 和 optimizable knowledge 的压力测试域。相同的 substrate pattern 可以通过替换对象词汇、约束库和领域模型迁移到其他工程领域：通信站点将机柜和冷机替换为天线、RRU、机柜、电源和站址布局约束；机械装配将设备连接替换为零件、配合、公差、载荷和干涉检查；能源系统将数据中心负载替换为发电设备、储能、并网、调度策略和可靠性约束。SD-HWE-Bench 则提供当前实现：ADL 工程声明、DTS 分层 critic、canonical lineage 任务抽取、actor 隔离运行和可归档评分结果。

本文按 NeurIPS Evaluations & Datasets Track 的口径组织贡献：evaluation 本身是研究对象，而非模型论文的附属实验。我们关心的是：当系统级工程任务被组织为不同的提交对象、约束反馈和知识条件时，agent 的成功率、失败模式、修复曲线和优化上限会如何变化。因此，本文的实验不以“某个模型最好”为主线，而以 evaluation design 如何改变可支持的科学结论为主线。

本文贡献如下：

1. 提出 Engineering as Code 作为面向 engineering agents 的 executable evaluation substrate，区别于单纯的工程设计表示或工具接口。
2. 将 representation、constraint、knowledge gaps 重新表述为 substrate 的三个必要能力：可闭环表征、可执行约束、可优化知识。
3. 给出基于 SD-HWE-Bench 与 AI Data Center Design 的三组受控实验，用于测量表征闭环能力、pseudo-correctness 与 repair 饱和、以及可优化知识对 Pareto frontier 的影响。本文当前保留结果表占位，所有具体数字将在正式实验归档后由 run artifacts 填充。
4. 给出 evaluation claims、assumptions、artifact contract 与 failure-mode taxonomy，讨论这种 substrate 如何把工程 agent 评估从“看起来正确”的自然语言方案，推进到“可验证正确”的工程闭合，并进一步推进到“前沿最优”的知识驱动协同设计。
