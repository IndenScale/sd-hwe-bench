<!-- markdownlint-disable MD041 -->
<!--
# 06 Orthogonality
位置：第 5.5 节 PDL、PML 和 PLL 的正交性
字数：约 205 词
目标：正文
-->

三种 ADL 子语言的正交性是实现增量校验、并行编辑和语义差异的核心设计原则。每个子语言位于各自的文件中：PDL 在 `instances/` 和 `models/`，PML 在 `mates/`，PLL 在 `layouts/layout.yaml`。由于命名空间分离，一个维度的变更不会重写另一个维度的文件。

**增量校验。** 智能体可以先生成 PDL 声明并通过 L0–L2 检查（语法、schema 和引用完整性）。只有在此之后才需要处理 PML Mate 约束（L2）和 PLL 空间规则（L3–L4）。这与编译器的分段错误反馈一致。

**并行编辑。** 设备工程师可以修改 `instances/SRV-01.yaml`，布局工程师可以修改 `layouts/layout.yaml`，机械工程师可以修改 `mates/rack-mount/RACK-A02-SRV-01.yaml`。由于文件相互独立，Git 合并冲突只发生在同一决策维度发生变更的地方。

**语义差异。** `instances/` 的 Git diff 表示“某些设备身份或属性发生变化”；`mates/` 的 diff 表示“某些耦合发生变化”；`layouts/layout.yaml` 的 diff 表示“某些位置发生变化”。例如：

```diff
- position_u: 10
+ position_u: 12
```

明确是一次布局变更，而对 `instances/SRV-01.yaml` 中 `tdp_w` 的修改则是一次电气变更。这种可解释性既支持人工代码审查，也支持 RLVR 训练中的自动化奖励归因。
