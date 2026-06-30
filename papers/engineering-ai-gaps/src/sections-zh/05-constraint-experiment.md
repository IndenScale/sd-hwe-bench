# 5. 实验二：约束鸿沟

本实验验证自然语言规范与可执行约束之间的差异。核心问题是：Agent 失败是否来自“不知道工程规则”，还是来自规则没有被转化为可执行反馈，从而无法在提交前发现 pseudo-correctness。

## 5.1 实验条件

对同一批任务设置三种条件：

| 条件 | Agent 可见内容 | 提交前检查 | 目的 |
|---|---|---|---|
| NL-only | 任务描述中的自然语言约束 | 无 | 测试自然语言要求是否足够 |
| Docs-only | 任务描述 + 多部规范文档目录 | 无 | 测试查阅规范能否避免遗漏 |
| Executable | 同样规范 + DTS/piki check | 有 | 测试可执行约束与 repair loop 的作用 |

Docs-only 条件应尽量模拟真实工程：规范分散在消防、防雷、结构、日照、维护空间、接口兼容、设备安装等目录中。Agent 可以阅读规范，但没有自动检查器在提交前告诉它遗漏了哪一条。

## 5.2 指标

我们定义两个核心指标：

```text
Pseudo-Correctness Rate =
  visually or verbally plausible submissions that fail executable critics
  / all plausible submissions
```

```text
Omission Density =
  missed required constraints / total applicable constraints
```

此外记录：

- repair 轮次与 pass rate 的关系。
- 失败约束所属专业：消防、防雷、结构、日照、接地、维护空间、接口、电源、热、施工。
- 失败层级：L1/L2 引用错误、L3 静态约束、L4 动态/调度、L5 几何/可建性。
- 任务规模与通过率的相关性。

## 5.3 预期发现

在 Executable 条件下，Agent 可能一开始仍失败，但通过 DTS 反馈和 repair loop 会迅速接近饱和。任务规模未必是主导因素；更重要的是约束是否可执行、错误是否局部化、反馈是否能被 Agent 消费。

在 NL-only 和 Docs-only 条件下，Agent 可能生成结构完整、术语专业、叙述合理的设计方案，但仍稳定遗漏跨规范约束。这类失败恰恰是工程 AI 中最危险的 pseudo-correctness：它们比明显错误更难被自然语言评审发现。

## 5.4 主张

约束鸿沟实验要支撑的结论是：

**工程 Agent 的真实性能不是模型单独决定的，而是模型与可执行约束环境共同决定的。自然语言规范可以表达要求，但不能充分构成评估；可执行约束把“看起来正确”转化为“可以被证明正确或定位错误”。**

## 5.5 待补实验

本节需要补充：

- 三种条件下的 pass@1、pass@k 和 repair 后 pass rate。
- pseudo-correctness 人工标注协议。
- Top omission constraints。
- 任务规模与饱和速度散点图。
