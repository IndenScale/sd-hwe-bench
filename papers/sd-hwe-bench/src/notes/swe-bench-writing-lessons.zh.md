# 从 SWE-bench / SWE-bench Multimodal 学到的论文写作框架

> 目标：把两篇 benchmark 论文的写作结构、叙事节奏和图表策略迁移到 SD-HWE-Bench（NeurIPS/ICLR Dataset & Benchmark Track）。

---

## 1. 标题公式

**SWE-bench**：`[名字]: Can [主体] [做某件事]?`  
→ *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?*

**SWE-bench Multimodal**：`[名字]: Do [主体] Generalize to [新维度]?`  
→ *SWE-bench Multimodal: Do AI Systems Generalize to Visual Software Domains?*

**SD-HWE-Bench 候选标题**：

- *SD-HWE-Bench: Can Language Model Agents Resolve Real-World Hardware Engineering Design Issues?*
- *SD-HWE-Bench: Do AI Systems Generalize to Executable Hardware Engineering Domains?*
- *SD-HWE-Bench: Evaluating LLM Agents on Multiphysics Hardware Design with Executable Digital Models*

---

## 2. 摘要黄金结构（约 150–200 词）

| 句子 | 功能 | SWE-bench 示例 | SD-HWE-Bench 改写 |
|---|---|---|---|
| S1 | 背景张力 | 语言模型发展速度超过评测能力 | 硬件设计 AI 助手兴起，但缺乏能反映真实工程复杂度的 benchmark |
| S2 | 现有 gap | 现有 benchmark 饱和/过短 | 现有 EDA/CAE benchmark 多为脚本级、单领域、不可执行 |
| S3 | 提出工作 | 我们提出 SWE-bench，2294 个真实 GitHub issue | 我们提出 SD-HWE-Bench，N 个来自 canonical ADL 工程的真实设计增量 |
| S4 | 任务定义 | 模型拿到 issue+代码库，生成 patch 通过测试 | 模型拿到设计增量描述+ADL 工程，生成修改并通过 ESA 静态/仿真验证 |
| S5 | 核心难点 | 跨文件、长上下文、执行交互 | 跨物理域、约束驱动、多模态信号、长上下文 |
| S6 | 主结果 | Claude2/GPT4 仅 4.8%/1.7% | 最强 Actor 在 pass@1 上仅 X%，repair 后 Y% |
| S7 | 开源贡献 | 发布训练集与 SWE-Llama | 发布 canonical ADL 工程、任务提取工具、ESA evaluation harness |

---

## 3. 引言三段式

### 3.1 第一段：大势所趋

- 大模型正在从代码补全走向仓库级/工程级自主系统。
- 引用 2–3 个近期工作（SWE-agent、Devin、Aider 等）。

### 3.2 第二段：现有 benchmark 不够

- 列表形式点出 3–4 个缺陷：
  1. 太简单/过饱和（HumanEval、MBPP）。
  2. 非执行评测（部分代码生成 benchmark）。
  3. 单领域/单语言（现有 EDA benchmark 多聚焦 RTL/PnR）。
  4. 缺乏真实工程约束（功耗、热、结构、信号完整性、可制造性）。

### 3.3 第三段：提出工作与卖点

- 一句话定义 SD-HWE-Bench。
- 列出 3–4 个优势（与 SWE-bench 对齐）：
  1. **真实场景**：canonical ADL 工程模拟真实硬件设计流程。
  2. **可执行评测**：ESA 静态检查 + 行为级仿真/网表验证。
  3. **跨物理域**：电源、散热、机械、信号完整性等多域耦合。
  4. **可持续更新**：基于 commit 历史持续生成新任务。

---

## 4. 数据构建：四/五阶段 Pipeline

参考 SWE-bench（3 阶段）和 SWE-bench M（5 阶段），SD-HWE-Bench 可设计为：

| 阶段 | 名称 | 输入 | 输出 | 写作要点 |
|---|---|---|---|---|
| 1 | Canonical 工程设计 | 领域专家设计 | 2–3 个完整 ADL 工程 | 说明为何选这些领域 |
| 2 | 版本化 commit 历史 | 工程迭代过程 | 带测试/约束的 commit 序列 | 每个 commit = 一个设计增量 |
| 3 | 任务提取 | commit k → commit k+1 | 任务实例（问题描述、上下文、 gold patch、测试） | 给出提取工具与元数据 schema |
| 4 | 执行验证 | ESA 环境 | 可复现的 pass/fail 信号 | 量化环境搭建成本 |
| 5 | 人工审核 | 作者/领域专家 | 剔除不可能任务，标注难度/必要性 | 给出标注协议与一致性 |

**漏斗数字**：例如 “3 个工程 → 1,200 个 commit → 486 个有效任务 → 人工审核后 420 个”。

---

## 5. 任务特性：列表 + 一句话解释

参考 SWE-bench 的 6 条特性，SD-HWE-Bench 可列出：

1. **真实硬件工程设计任务**：完整 ADL 工程，包含网表、约束、几何、仿真配置。
2. **多物理域耦合**：单个任务可能同时涉及电气、热、结构、制造约束。
3. **长上下文**：ADL 工程通常包含数千行描述、数十个模块、多个仿真报告。
4. **可执行数字模型**：每个任务都绑定 ESA 静态检查与行为级/指标级验证。
5. **跨抽象层编辑**：修改可能发生在 schema、模块实例、约束、几何、测试任一层面。
6. **可持续更新**：新的设计迭代可随时抽取为新任务，避免数据污染。

---

## 6. 必须有的 5 张核心表

| 表号 | 内容 | 作用 |
|---|---|---|
| Table 1 | 任务规模统计（issue 长度、ADL 行数/模块数、修改范围、测试数） | 让读者直观感受任务复杂度 |
| Table 2 | 与现有 benchmark 对比（领域、执行评测、多物理域、任务来源） | 定位 novelty |
| Table 3 | 模型/Agent 上下文能力（最大 token、覆盖 oracle 上下文比例） | 解释某些模型天然劣势 |
| Table 4 | 主结果：各 Actor/模型 pass@1 / cost / time | 核心贡献 |
| Table 5 | 消融实验（完整上下文 vs. oracle 模块 vs. collapsed 信号） | 解释失败原因 |

---

## 7. 必须有的 4 张核心图

| 图号 | 内容 | 作用 |
|---|---|---|
| Figure 1 | SD-HWE-Bench 整体 pipeline（canonical 工程 → commit → task → ESA） | 视觉化故事 |
| Figure 2 | 任务在各领域/仓库的分布 | 展示多样性 |
| Figure 3 | 不同 Actor 解决率随上下文长度变化 | 分析上下文淹没 |
| Figure 4 | 失败模式分解（静态检查失败、仿真失败、约束违反、patch 格式错误） | 深入诊断 |

---

## 8. 实验设计：三个检索/上下文设置

直接借鉴 SWE-bench：

1. **Full context**：把完整 ADL 工程塞给模型（受上下文限制）。
2. **Oracle context**：只给参考 commit 修改过的模块/文件（能力上限）。
3. **Collapsed context**：只保留被修改行 ±N 行（定位能力上限）。

**衍生实验**：

- 有/无仿真反馈（ESA）对比；
- 有/无几何/约束图对比（验证多模态信号必要性）；
- patch 生成 vs. 整模块重写；
- repair loop 0/1/5/20 轮对比。

---

## 9. 相关工作三层结构

### 9.1 第一层：LM 评测

- 指出通用 benchmark（MMLU、BIG-bench、HELM）“拼盘式”缺点：每个任务太窄，无法体现工程级综合能力。

### 9.2 第二层：代码/硬件生成 benchmark

- HumanEval、MBPP、MultiPL-E、ClassEval、RTL/EDA benchmark。
- 共同局限：短、自包含、单领域、缺乏真实工程反馈。

### 9.3 第三层：ML for SE / EDA

- 程序修复、commit 生成、PR review、bug 定位、自动化测试。
- 与 SD-HWE-Bench 关系：我们提供一个更大规模、更真实、可执行的平台，兼容这些方法。

---

## 10. 讨论与结论写作模板

### 10.1 局限（Limitations）

1. 当前仅覆盖数字/电源/热/机械键盘等少数领域；未来扩展模拟/射频/光学。
2. 基线方法简单，不限制未来方法；鼓励 agent、多模态模型、领域求解器。
3. 仅依赖 ESA 执行评测不足以完全保证设计质量；还需人工可读性/可制造性审查。
4. 任务从 canonical 工程抽取，可能与真实企业设计流程有差异。

### 10.2 结论

> 真实硬件工程的复杂度远超代码补全。SD-HWE-Bench 借助可计算工程表示层（ADL）与确定性执行反馈（ESA），真实再现了物理设计的约束环境。这一更真实的评测平台将推动更实用、更智能、更自主的 LM Agent 在硬件工程领域的发展。

---

## 11. 可复现性与伦理声明要点

- 全部 canonical 工程与任务元数据将开源；
- 不依赖敏感企业数据；
- 提供 Docker/uv 一键复现环境；
- 提供任务生成、评测、基线 Actor 的完整代码；
- 明确许可证与引用方式。

---

## 12. 写作检查清单

- [ ] 标题是疑问句或清晰的主张句，包含 “Can/Do/Evaluating” 等动词。
- [ ] 摘要 7 句话覆盖背景、gap、工作、任务、难点、结果、开源贡献。
- [ ] 引言三段式：背景 → 现有缺陷 → 本文工作与优势。
- [ ] 数据构建有明确 pipeline 与漏斗数字。
- [ ] 列出 4–6 条任务特性，每条配一句话解释。
- [ ] 至少 5 张表：规模统计、对比表、上下文能力、主结果、消融。
- [ ] 至少 4 张图：pipeline、分布、上下文影响、失败分解。
- [ ] 结果不仅给解决率，还给 apply 率、cost、time、repair 轮数。
- [ ] 分析失败原因，而非只报数字。
- [ ] 相关工作分 3 层，每层点出共同局限。
- [ ] 讨论诚实写局限，结论升华到“更真实/更自主”的愿景。
