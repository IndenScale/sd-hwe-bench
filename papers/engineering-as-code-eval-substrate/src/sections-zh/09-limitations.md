# 9. 局限性

本文仍有若干局限。

第一，SD-HWE-Bench 目前主要覆盖 telecom 与 AIDC 场景，尚不能代表机械、HVAC、管道、机器人、航空航天等全部系统级工程领域。本文提出的是 substrate 设计原则和 reference implementation，而不是宣称任务覆盖已经完整。

第二，ADL 是一种研究型工程表征，并非成熟工业标准。本文比较的是 agent evaluation 所需的闭环能力，而不是声称 ADL 可以替代 CAD/BIM/PLM/EDA 等工业软件。实际工业部署可能需要把 EaC 与现有工具链双向同步。

第三，约束实验中的 pseudo-correctness 需要人工标注协议辅助定义。虽然可执行 critic 能发现大量错误，但“看起来合理”这一维度仍包含主观判断，需要明确标注指南和一致性统计。

第四，知识实验目前计划作为 AIDC 小规模 probe。它能展示设计-调度联合优化和可优化知识的上限差异，但不足以穷尽所有工程领域中的知识传播问题。真实供应商报价、设备故障率、现场施工数据和运营数据仍需要进一步接入。

第五，本文没有直接提出新的模型训练算法。我们的贡献在于 evaluation substrate、实验协议和 failure mode 分解；后续可以基于 DTS 反馈构建 repair policy、RLVR 环境、主动约束发现或跨层优化 agent。
