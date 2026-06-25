# SWE-bench 论文结构化分析（中文）

> **原文**：SWE-bench: Can Language Models Resolve Real-World GitHub Issues?  
> **作者**：Carlos E. Jimenez*, John Yang*, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, Karthik R. Narasimhan  
> **发表**：ICLR 2024  
> **arXiv**：2310.06770  
> **数据来源**：ar5iv HTML 结构化提取  

---

## 1. 核心贡献一句话

把真实 GitHub issue → merged PR 的 workflow 变成可自动评测的 benchmark，首次在“仓库级代码编辑”场景下系统评估了大语言模型解决真实软件工程问题的能力。

---

## 2. 摘要（Abstract）翻译与提炼

> 语言模型的发展速度已经超过我们的评测能力；要推动其未来发展，必须研究它们的能力边界。真实软件工程是一个丰富、可持续且极具挑战性的测试场景。我们提出 **SWE-bench**：一个包含 **2,294** 个软件工程问题的评测框架，问题来自 **12** 个流行 Python 仓库的真实 GitHub issue 与对应 pull request。模型拿到 issue 描述和完整代码库后，需要编辑代码库以解决问题。SWE-bench 要求模型理解并协调跨多个函数、类乃至文件的修改，远超传统代码生成任务。评测显示，最先进的模型只能解决最简单的问题：Claude 2 与 GPT-4 在 oracle 检索下分别仅解决 **4.8%** 和 **1.7%** 的实例。为支持开放模型研究，我们还发布了 **19,000** 条训练数据，并微调出 **SWE-Llama（7B/13B）**。

**写作可借鉴点**：
- 首句用“模型能力超越评测能力”制造张力；
- 第二句直接点出 gap（真实软件工程 vs. 现有 benchmark）；
- 用具体数字（2,294 / 12 / 4.8% / 1.7%）立刻给出规模与难度；
- 明确 release 的训练数据与模型，降低复现门槛。

---

## 3. 引言（Introduction）框架

### 3.1 三段式结构

| 段落 | 功能 | 原文要点 |
|---|---|---|
| P1 | 背景与动机 | LMs 已大规模部署，但现有 benchmark 趋于饱和，无法捕捉前沿能力。 |
| P2 | 好 benchmark 的标准 | 任务要足够难，但预测结果又要易于验证；代码任务天然适合用单元测试验证。 |
| P3-P4 | 从理想任务到真实任务 | HumanEval 等是自包含小任务；真实 bug 修复需要跨文件、长上下文、复杂推理。 |
| P5 | 提出 SWE-bench | 从 GitHub issue + merged PR 构建任务，生成 patch，用真实测试框架评测。 |
| P6-P8 | 优势、结果、开源贡献 | 真实场景、多样输入、可扩展、执行评测；Claude 2 / GPT-4 表现很差；发布 SWE-bench-train 与 SWE-Llama。 |

### 3.2 关键写作句式（可直接改写）

- “Existing benchmarks have become saturated and fail to capture the frontier of what state-of-the-art LMs can and cannot do.”
  → 现有 benchmark 已经饱和，无法刻画最新模型的能力边界。
- “Building a good benchmark is difficult since tasks must be challenging enough to stump existing models, but model predictions must also be easy to verify.”
  → 好的 benchmark 必须既能让现有模型束手无策，又能方便验证预测结果。
- “SWE-bench offers several advantages over existing LM programming benchmarks: a realistic setting, diverse inputs, a robust execution-based evaluation framework, and the ability to continuously update.”
  → 我们的 benchmark 在真实场景、输入多样性、鲁棒执行评测、可持续更新四方面优于现有代码生成 benchmark。

### 3.3 图 1 描述

> SWE-bench 从真实 Python 仓库中连接 GitHub issue 与合并后的 PR 解决方案，这些 PR 解决了相关测试。模型拿到 issue 文本与代码库快照后生成 patch，再与真实测试对比。

**对应 SD-HWE-Bench**：可将图 1 替换为“issue/commit 设计增量 → ADL 工程 → ESA 静态/动态反馈”的 pipeline。

---

## 4. SWE-bench 任务构建（第 2 节）

### 4.1 任务定义

- **输入**：issue 文本 + 完整代码库。
- **输出**：patch 文件（指定修改哪些行）。
- **评测**：用 `patch` 命令应用生成 patch，然后执行相关单元/系统测试；全部通过即算解决。
- **主指标**：`% Resolved`（成功解决的任务比例）。

### 4.2 三阶段数据收集管线

| 阶段 | 操作 | 过滤后规模 |
|---|---|---|
| Stage I | 从 12 个流行 Python 仓库收集 merged PR | ~90,000 PRs |
| Stage II | 属性过滤：PR 必须关联一个 issue，且修改了测试文件 | 候选集 |
| Stage III | 执行过滤：必须有至少一个 test 从 fail → pass；排除安装/运行错误 | 2,294 实例 |

**写作可借鉴点**：
- 用“三阶段管线”把复杂的数据构建过程模块化；
- 每个阶段明确输入/输出/过滤标准；
- 用漏斗数字（90k → 2,294）体现质量筛选的严格。

### 4.3 SWE-bench 的六大特性

1. **真实软件工程任务**：大代码库 + 真实 issue，需要资深工程师才具备的技能。
2. **可持续更新**：收集流程可自动应用于任意 Python 仓库，几乎无需人工干预。
3. **长输入多样性**：issue 平均 195 词，代码库平均 438K 行、数千文件。
4. **鲁棒评测**：每个实例至少 1 个 fail-to-pass 测试，40% 有 ≥2 个；中位数额外 51 个 pass-to-pass 测试。
5. **跨上下文代码编辑**：不限于函数/类，平均修改 1.7 个文件、3.0 个函数、32.8 行。
6. **解决方案空间宽广**：允许模型生成与参考 PR 不同的创新解。

**对应 SD-HWE-Bench**：
- 真实任务 → canonical ADL 工程 + commit 历史提取的设计增量；
- 可持续更新 → 只要维护 canonical 工程，就能不断生成新任务；
- 鲁棒评测 → ESA 静态检查 + 行为级仿真/测试；
- 跨上下文编辑 → ADL 工程跨模块（power/thermal/mechanical）修改。

### 4.4 Table 1 关键统计（已清洗）

| 属性 | 均值 | 最大值 |
|---|---|---|
| Issue 长度（词） | 195.1 | 4,477 |
| 代码库文件数（非测试） | 3,010 | 5,890 |
| 代码库行数（非测试） | 438K | 886K |
| Gold patch 编辑行数 | 32.8 | 5,888 |
| Gold patch 编辑文件数 | 1.7 | 31 |
| Gold patch 编辑函数数 | 3.0 | 36 |
| Fail-to-pass 测试数 | 9.1 | 1,633 |
| 总测试数 | 120.8 | 9,459 |

**用途**：用于论证“任务规模远超 HumanEval”。SD-HWE-Bench 也应给出类似的“issue/设计增量 + 代码库规模 + 修改范围 + 测试数量”统计表。

---

## 5. SWE-Llama 微调模型（第 3 节）

### 5.1 目的

在专有模型之外提供开放模型基线，证明开源模型也能处理长上下文仓库级编辑。

### 5.2 做法

- **训练数据**：从另外 37 个仓库收集 19,000 issue-PR 对；与测试仓库互不重叠，避免污染。
- **模型**：基于 CodeLlama-Python 7B / 13B。
- **训练方式**：LoRA 微调 attention 子层；剔除 >30k tokens 的序列；有效训练集约 10,000 条。

### 5.3 写作可借鉴点

- 开源贡献单独成节，显得完整；
- 强调“训练/测试仓库不相交”以打消数据污染疑虑；
- 给出模型规模、微调方法、有效训练量，便于复现。

---

## 6. 实验设置（第 4 节）

### 6.1 检索方式

由于代码库远超上下文窗口，采用两种检索设置：

- **Sparse retrieval（BM25）**：用自然语言 issue 检索代码文件，分别设 13k/27k/50k token 上限。
- **Oracle retrieval**：直接使用参考 PR 修改过的文件（不现实但用于定位能力上限）。

### 6.2 模型与上下文

| 模型 | 最大 tokens | Oracle 文件覆盖率 |
|---|---|---|
| ChatGPT-3.5 | 16k | 58.1% |
| GPT-4 | 32k | 84.1% |
| Claude 2 | 100k | 96.4% |
| SWE-Llama | ≥100k | ≥94.8% |

### 6.3 输入格式

任务指令 + issue 文本 + 检索到的文件/文档 + 示例 patch 文件 + 生成 patch 的提示。

**对应 SD-HWE-Bench**：
- 我们的“上下文”不仅是代码文件，还包括 ADL schema、netlist、约束、仿真结果；
- 可以设计“oracle 上下文”= 参考 commit 修改的模块/文件；
- 示例 patch 可替换为“ADL 增量示例”。

---

## 7. 结果与分析（第 5 节）

### 7.1 主结果 Table 5（已清洗）

| 模型 | BM25 % Resolved | BM25 % Apply | Oracle % Resolved | Oracle % Apply |
|---|---|---|---|---|
| ChatGPT-3.5 | 0.20 | 10.50 | 0.52 | 12.38 |
| Claude 2 | 1.96 | 29.86 | 4.80 | 47.00 |
| GPT-4* | 0.00 | 4.50 | 1.74 | 13.20 |
| SWE-Llama 7B | 0.70 | 37.84 | 3.00 | 54.80 |
| SWE-Llama 13B | 0.70 | 39.41 | 4.00 | 52.10 |

*GPT-4 在 oracle/BM25 27k 上仅评测 25% 子集。

### 7.2 关键分析结论

1. **跨仓库难度差异**：各模型在不同仓库上趋势相似，但解决集合重叠度低。
2. **上下文长度与难度负相关**：输入越长，Claude 2 表现越差，说明模型在“token 大海”中定位问题代码困难。
3. **Oracle-collapsed 实验**：只保留 gold patch 编辑行 ±15 行上下文，GPT-4 从 1.3% → 3.4%，Claude 2 从 4.8% → 5.9%。
4. **微调模型对上下文分布敏感**：SWE-Llama 用 oracle 训练，遇到 BM25 检索结果时性能骤降。
5. **生成 patch 优于生成整文件**：Claude 2 oracle 下 patch 4.8% vs. 整文件 2.2%。
6. **模型编辑偏短**：成功 patch 平均不到 gold patch 一半长度，且很少改多个文件。

**对应 SD-HWE-Bench**：
- 可做“完整 ADL 上下文 vs. oracle 模块上下文 vs. Collapsed 上下文”的消融；
- 比较“生成 ADL 增量 vs. 重写整个模块”的效率；
- 分析失败是否因为“上下文淹没”而非工程理解不足。

---

## 8. 相关工作（第 6 节）写作策略

### 8.1 三个层次

| 层次 | 内容 | 作用 |
|---|---|---|
| LM 评测 | Dynabench、BIG-bench、HELM 等 | 指出现有 benchmark “拼盘式”任务的缺点：每个任务太窄、太简单。 |
| 代码生成 benchmark | HumanEval、MultiPL-E、ClassEval 等 | 说明它们多局限于函数/类、单语言、封闭形式完成。 |
| ML for SE | 自动化 commit、PR review、bug 定位、测试、程序修复 | 定位 SWE-bench 与这些工作的关系：提供更大规模、更真实的评估平台。 |

### 8.2 可借鉴写法

- 不堆砌引用，而是每组 2–3 个代表作，点出它们的共同局限；
- 用一句话把 SWE-bench 定位成“兼容并超越这些工作”；
- 强调“真实世界”与“可扩展性”两个差异化关键词。

---

## 9. 讨论与结论（第 7 节）

### 9.1 局限与未来方向

1. 仅覆盖 Python；未来扩展到更多语言/领域。
2. 基线方法最简单，不限制未来方法；鼓励 agent、更大模型、程序分析工具。
3. 仅依赖执行测试不足以保证可靠性；模型生成代码可能不够全面、高效、可读。

### 9.2 结论

> 真实软件开发复杂度远超代码补全。SWE-bench 借助开源协作流程，真实再现了现实编码环境，鼓励具有直接实用价值的创新方案。

**对应 SD-HWE-Bench**：
- 局限可写：目前仅覆盖数字/机械/热设计等领域，未来扩展模拟/射频/光学；
- 结论可强调“工程表示层 + 确定性反馈”是物理工程设计智能化的关键基础设施。

---

## 10. 伦理与可复现声明

- **伦理**：全部来自公开仓库，遵守许可证；不收集用户信息；无人类被试。
- **可复现**：提交完整源码压缩包；包含 2,294 条任务实例；计划开源完整仓库与文档。

**对应 SD-HWE-Bench**：
- 强调 canonical 工程与任务均为原创/授权，无真实企业敏感数据；
- 提供 Docker/uv 环境、完整 evaluation harness、训练数据生成脚本。

---

## 11. 对 SD-HWE-Bench 论文写作的启示

| 维度 | SWE-bench 做法 | SD-HWE-Bench 对应 |
|---|---|---|
| **标题** | 疑问句 + 核心能力 | “Can LLM Agents Resolve Real-World Hardware Engineering Design Issues?” |
| **摘要** | 3 个数字 + 1 个核心 gap + 1 个开源贡献 | 给出 ADL 任务数、仓库/领域数、pass@1、以及 ADL/ESA 开源 |
| **引言** | 三段式：背景 → 好 benchmark 标准 → 提出工作 | 背景（硬件设计 AI 辅助） → 现有 benchmark 缺陷 → SD-HWE-Bench |
| **数据构建** | 三阶段 pipeline + 漏斗数字 | canonical 工程 → commit 提取 → ESA 验证；给出每步数量 |
| **任务特性** | 列 6 条并逐一解释 | 列 ADL 任务特性：多物理域、约束驱动、长上下文、确定性反馈 |
| **统计表** | Table 1 规模统计 | 任务规模表：issue 长度、ADL 行数/模块数、修改范围、测试数 |
| **实验** | BM25 / Oracle / Collapsed 消融 | 完整上下文 / Oracle 模块 / Collapsed 信号 消融 |
| **结果表** | Table 5 多模型 % Resolved / % Apply | 多 Actor/模型 pass@1 / cost / repair 轮数 |
| **相关工作** | 三层结构 | LM 评测 → 代码/硬件生成 benchmark → ML for EDA/CAE |
| **讨论** | 局限 + 未来方向 + 结论 | 局限（领域/语言/视觉） + 未来（agent、多物理、制造约束） |

---

## 12. 可直接引用的关键数字

- 任务数：**2,294**
- 仓库数：**12**
- 训练集：**19,000** issue-PR 对，来自 **37** 个仓库
- Claude 2 oracle 解决率：**4.8%**
- GPT-4 oracle 解决率：**1.7%**
- Claude 2 BM25 解决率：**1.96%**
- issue 平均长度：**195 词**
- 代码库平均行数：**438K**
- 平均修改文件数：**1.7**；函数数：**3.0**；行数：**32.8**
