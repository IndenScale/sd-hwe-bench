# 9. 局限性

本文仍有若干局限。

第一，PEaC-Bench 目前主要覆盖 telecom 与 AIDC 场景，尚不能代表机械、HVAC、管道、机器人、航空航天等全部系统级物理工程领域。本文提出的是 substrate 设计原则和 reference implementation，并不宣称任务覆盖已经完整。

第二，ADL 是一种研究型工程表征，并非成熟工业标准。本文比较的是 agent evaluation 所需的闭环能力，不声称 ADL 可以替代 CAD/BIM/PLM/EDA 等工业软件。实际工业部署可能需要把 EaC 与现有工具链双向同步。

第三，约束实验中的 pseudo-correctness 需要人工标注协议辅助定义。虽然可执行 critic 能发现大量错误，但“看起来合理”这一维度仍包含主观判断，需要明确标注指南和一致性统计。

第四，知识实验目前计划作为 AIDC 小规模 probe。它能展示设计-调度联合优化和可优化知识的上限差异，但不足以穷尽所有工程领域中的知识传播问题。真实供应商报价、设备故障率、现场施工数据和运营数据仍需要进一步接入。

第五，本文没有直接提出新的模型训练算法。我们的贡献在于 evaluation substrate、实验协议和 failure mode 分解；后续可以基于 DTS 反馈构建 repair policy、RLVR 环境、主动约束发现或跨层优化 agent。

第六，当前中文稿中的第 5 章约束实验数字来自 **{{ data.eval_substrate.artifact.result_label }}**，但实验规模仍然有限：1 个模型、2 个 AIDC 长程任务、2 个可执行反馈条件、12 条有效 attempt。它足以支持 frozen baseline 下的 diagnostic-contract 分析，但不能替代完整 NL-only / Docs-only / multi-model 投稿矩阵。第 4 章表征实验和第 6 章知识实验仍为待补协议，不应被当作正式结果。若 artifact 与趋势性分析冲突，应优先修改分析，不能反向调整结果。

第七，E&D artifact 需要处理匿名化、长期可用性和机器可读元数据。PEaC-Bench 作为可执行 artifact，原则上需要在投稿时提供匿名代码、任务、数据卡、运行说明、30 分钟小样本检查路径、完整复现实验路径、license、expected output、scorer determinism 说明和 actor isolation 说明；如果某些 AIDC 参数来自非公开来源，必须替换为合成或可公开参数，并明确说明其对外部效度的影响。若按 dataset/benchmark 类 submission 提交，还需要准备 Croissant core 与 Responsible AI metadata，并保证 reviewer 可以通过公开或匿名 URL 访问 artifact。
