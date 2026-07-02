# 8. 讨论

## 8.1 为什么 Substrate 比任务规模更重要

如果本文被理解为“一个小规模硬件工程 benchmark”，贡献会被低估。本文真正讨论的是 physical engineering evaluation substrate：工程状态如何提交，系统如何判定，错误如何定位，修复如何发生，知识如何进入优化。规模当然重要，但规模必须建立在正确的评估单元上。一个包含大量自然语言工程问答的数据集，未必比一个小规模但可提交、可检查、可 repair、可分析 failure mode 的 substrate 更能推动物理工程评估。

NeurIPS E&D 语境下，本文更接近 evaluation science 和 artifact methodology：定义可复现评估对象、可执行评分协议、failure mode taxonomy 和受控实验轴。AIDC reference implementation 的价值也不取决于覆盖所有数据中心设计细节；它提供的是一个高耦合场景，迫使表征、约束和知识三类能力同时暴露。

## 8.2 防误读边界

本文有五个容易被误读的位置。第一，PEaC-Bench 不是以任务规模取胜的小型 AIDC benchmark；主张是 evaluation substrate 和 controlled evaluation design。第二，ADL 不是要替代 CAD、BIM、OpenSCAD 或 PLM；贡献在于 submit-check-diagnose-repair-optimize 闭环，而不是又发明一种 DSL。第三，实验不是为了证明某个模型或系统强于弱 baseline；实验变量是 representation interface、constraint executability、diagnostic granularity 和 knowledge condition。第四，Knowledge claim 不是完整工业数据中心优化声明；它是 bounded AIDC probe，用公开与合成参数测试 frontier shift 和 margin decomposition。第五，本文不能停留为 position paper；投稿版必须用真实 runs、真实表格、可复现 artifact 和 failure taxonomy 支撑这些边界。

## 8.3 为什么当前稿件不能停留在 Protocol

本文的核心论述不依赖某个具体模型在某个任务上的绝对分数，而依赖 evaluation design 的因果结构：agent 提交什么、能看到什么反馈、最终由什么 critic 判定、失败如何归因、repair 如何发生、知识如何进入目标函数。这些结构在实验运行前就必须被定义清楚，否则结果表只会变成普通 leaderboard。

但 E&D 投稿版不能停留在 protocol。当前中文稿可以冻结三类实验轴：表征闭环、约束可执行性、知识可优化性；正式投稿版必须进一步完成三件事：用 run artifacts 填充主文结果表，用图展示 repair curve、violation layer distribution 和必要的 frontier plot，用结果改写机制解释。如果最终数字与当前机制预期不一致，论文不应硬改成“预期正确”，而应把差异作为 E&D 发现：例如任务过于饱和、文档条件已足够强、诊断粒度收益有限、或 AIDC 知识库不足以推动 frontier。这样的负结果仍然服务于 evaluation science。

## 8.4 IC/EDA 是 Favorable Case 而不是 Representative Case

已有 IC/EDA 和板级电路 HWE benchmark 的成功，说明本文讨论的 substrate 条件并非人为发明的抽象概念，而是工程评估能够成立的必要支撑。RTL bug repair benchmark 能 work，是因为 RTL repository patch、EDA 编译仿真、testbench 和项目验证流已经构成了类似软件工程的闭环。Board-level schematic benchmark 能 work，是因为 schematic/netlist、datasheet、ERC 和 circuit simulation 在板级电路中已经形成了提交-检查-反馈路径。

但这并不意味着 general engineering benchmark 问题已经解决。IC/EDA 是 favorable case：它高度代码化，工具链成熟，验证文化强，PDK/datasheet/spec/testbench 等知识已经部分被工具消费。多数系统级工程没有这样的天然底座。AI data center、通信站点、机械装配、能源系统和施工排程中的反馈通常分散在 CAD/BIM、PDF、Excel、商业 GUI、供应商手册、仿真软件和人工审查流程里。

因此，本文并不否认已有 HWE benchmark 的价值；我们抽象出它们成立的原因，并追问如何把这种 substrate 条件显式构造到更广泛的系统级工程中。EaC 的价值在于把 IC/EDA 中“天然存在”的 representation、constraint 和 knowledge loop，转化为其他工程领域也可复用的 evaluation substrate 设计原则。

## 8.5 可执行约束会不会让任务太简单

可执行约束可能使许多任务在 repair loop 后迅速饱和。这种饱和不是缺陷，而是科学发现：当约束完备且反馈可消费时，agent 可以像软件工程中的开发者一样迭代修复。一个好的 benchmark 不应只追求让模型失败，而应区分失败发生在哪一层。

如果低耦合任务在完整 critic 下快速饱和，说明表征和约束闭环已经足以支撑局部工程修复。真正困难的任务会转移到三个方向：约束不完备或跨规范分散时的遗漏，长程多变量动态耦合优化，以及知识更新和前沿工艺能力进入优化循环。这样的转移本身就是 substrate 提供的诊断价值。

## 8.6 为什么 AIDC 是 Reference Domain 而不是单一应用

AI Data Center Design 同时覆盖设计、建造和运营：机柜、服务器、液冷、供配电、储能、光伏、冷机、建筑空间、吊装、施工排程、电价、气候、负载和生命周期成本。它既能触发表征问题，也能触发约束问题，还能触发知识优化问题。因此，AIDC 在本文中承担的是 physical engineering evaluation 压力测试域，而非热门应用展示。

这并不意味着 EaC 只能用于 AIDC。相反，AIDC 的作用类似 reference implementation：如果一个 substrate 能在 AIDC 中表达对象、约束、诊断、repair 和优化，那么同样的 substrate 设计原则可以迁移到通信站点、机械装配、能源系统、施工排程和其他系统级工程领域。

## 8.7 从合规到最优

物理工程评估底座的发展路径可以分为三阶段：

1. **可表征**：工程状态能被机器提交、diff 和修改。
2. **可验证**：提交能被可执行约束判定，并产生可消费诊断。
3. **可优化**：前沿知识能进入跨层搜索，推动 Pareto frontier 外移。

PEaC-Bench 目前主要覆盖前两阶段，并通过 AIDC probe 开始触及第三阶段。未来工作需要更丰富的供应商知识、项目成本、施工资源、真实运营数据和参考优化器，以便把 PEaC substrate 从可验证工程闭合推进到可优化工程智能。
