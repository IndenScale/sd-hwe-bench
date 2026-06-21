<!-- markdownlint-disable MD041 -->
<!--
# 01 Rlvr And Sd Hwe Bench
位置：附录 V-A — RLVR 与 SD-HWE-Bench
字数：约 400 词
目标：附录
-->

# RLVR 与 SD-HWE-Bench

可验证奖励强化学习（Reinforcement Learning with Verifiable Rewards，RLVR）是 EaC 范式的终极使能器。其核心思想是用可自动判定的正确性信号替代昂贵的人工奖励模型或人工标注，从而以较低成本训练出能够解决复杂设计任务的智能体 [@shao2024deepseekmath; @deepseek2025r1; @sweagent2025swerl]。

## RLVR 因果链

代码、数学与芯片三个领域的成功共同验证了以下因果链：

```text
结构化可验证正确性表示 → 秒级确定性反馈 → RLVR 训练有效 → Agent 能力跃迁
```

- **数学**：DeepSeekMath 使用 GRPO（Group Relative Policy Optimization），以可验证的数学答案作为奖励信号，在无需人工奖励模型的情况下提升推理能力 [@shao2024deepseekmath]。
- **通用推理**：DeepSeek-R1 将同一范式扩展到大规模通用推理训练，证明 RLVR 不仅限于数学 [@deepseek2025r1]。
- **代码修复**：SWE-RL 证明，当测试套件提供确定性 Pass/Fail 信号时，强化学习能显著提升 bug 修复成功率 [@sweagent2025swerl]。

这三个证据点共同说明：**只要存在结构化、自动可判定的正确性表示，RLVR 就能在相应领域建立有效训练闭环**。

## 当前试点验证

在 SD-HWE-Bench 完成并发布之前，本文以 piki 原型和三个样本项目作为**小规模试点实验**，对信息表示假说进行初步验证。验证指标包括：

- **表达能力**：ADL 能否完整声明一个真实电信机架设计（样本 01）？
- **校验速度**：`piki check` 是否在秒级内完成 L0–L4a 检查？
- **规则覆盖**：64 条规则是否覆盖关键业务与几何约束？
- **生成物可用性**：`piki generate` 是否产出 BOM、机柜面板、端口映射等下游交付物？

样本 01 通过全部规则并生成 10 种交付物；样本 02 与 03 因布局与几何问题失败，被作为当前能力边界诚实披露（详见附录 V-C）。这一试点为假说提供了初步支持，但规模有限，不足以 claim 普遍结论。

## SD-HWE-Bench 的规划

SD-HWE-Bench（Software-Defined Hardware Engineering Benchmark）是首个面向 EaC 范式的能力评估基准，**正在设计中**，用于在更大规模上验证信息表示假说。其核心范式为：

```text
输入：自然语言工程需求
输出：结构化 ADL 声明（piki YAML）
评分：L0–L4 规则检查 Pass@k + 生成物质量 + L6 签收评估
```

与 SWE-Bench 不同，SD-HWE-Bench 评估的是从零创建设计声明的能力，而非修改现有代码库 [@jimenez2024swebench]。由于声明式工程设计实践本身尚不存在，SD-HWE-Bench 采用“定义性”策略：手工构建任务，诚实披露覆盖边界，并以规则检查通过率作为客观奖励信号。

## 初始任务域：电信机架部署

首个任务域选择电信机架部署，原因在于它是当前 ADL 与规则引擎能力边界内“最干净”的场景：

- **空间离散**：设备位置以机架 U 位为单位，避免连续 3D 约束求解；
- **约束代数化**：功率预算、承重、U 位冲突等约束多为代数不等式；
- **接口可枚举**：SFP28、RJ45、IEC-C13/C14 等接口类型数量有限；
- **验证快速**：`piki check` 可在 200 毫秒内完成 L0–L4a 校验，满足 RLVR 对反馈速度的要求。

## 与论文 B 的分工

SD-HWE-Bench 的完整实验设计、智能体实现与大规模评估将发表为论文 B（companion paper）。本文聚焦 EaC 的语言、机制与原型验证，并以 piki 样本项目提供**初步试点证据**；SD-HWE-Bench 作为后续大规模验证的规划出现。
