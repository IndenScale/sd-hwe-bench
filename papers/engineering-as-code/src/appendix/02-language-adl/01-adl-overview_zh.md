<!-- markdownlint-disable MD041 -->
<!--
# 01 Adl Overview
位置：第 5 节 ADL：装配定义语言（开篇 / 5.1）
字数：约 213 词
目标：正文
-->

ADL（Assembly Definition Language，装配定义语言）是 Engineering as Code 的核心声明式设计符号。它刻意采用*文本原生*的表达方式：设计意图以 YAML 编写并由代码校验，而非作为 CAD 或 BIM GUI 中的几何操作来捕获。ADL 由 piki 仓库中的 `adl/` 包实现（`adl/src/adl/`），并由 `src/piki/` 中的 piki 编排层消费。

该语言围绕三种正交子语言组织。**PDL**（Part Definition Language，部件定义语言）声明存在什么：Part 族、型号、实例及其接口。**PML**（Part Mating Language，部件装配语言）声明部件如何耦合：机械配合、电源配对、信号连接与守恒约束。**PLL**（Part Layout Language，部件布局语言）解析剩余的空间自由度：机架 U 位、楼层坐标，或装配树中的相对变换。这种分离在 `adl/docs/concepts/01-layered-model.md` 中定义，并由 ADL 校验器（`adl/src/adl/validation/validator.py`）强制执行。

ADL 的设计目标有三点：

1. *文本原生*表示，使智能体能够读写设计意图；
2. *面向智能体*的语法，具备文件级粒度、显式引用和确定性校验；
3. 身份、关系与空间之间的*正交性*，使得一个维度的变更不会扩散到其他维度。

piki 是加载 ADL 声明、运行分层规则引擎并生成下游交付物的参考运行时，但语言本身独立于任何单一工具而定义。
