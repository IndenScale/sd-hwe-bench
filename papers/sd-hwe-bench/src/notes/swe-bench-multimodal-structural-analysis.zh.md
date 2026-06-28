# SWE-bench Multimodal 论文结构化分析（中文）

> **原文**：SWE-bench Multimodal: Do AI Systems Generalize to Visual Software Domains?  
> **作者**：John Yang*, Carlos E. Jimenez*, Alex L. Zhang, Kilian Lieret, Joyce Yang, Xindi Wu, Ori Press, Niklas Muennighoff, Gabriel Synnaeve, Karthik R. Narasimhan, Diyi Yang, Sida I. Wang, Ofir Press  
> **发表**：ICLR 2025  
> **arXiv**：2410.03859  
> **数据来源**：ar5iv HTML 结构化提取  

---

## 1. 核心贡献一句话

在 SWE-bench 的基础上，把任务拓展到**带视觉元素的 JavaScript 前端/可视化软件领域**，首次系统评估 AI 系统能否跨语言、跨模态地解决真实软件工程问题。

---

## 2. 摘要（Abstract）翻译与提炼

> 自主软件工程系统已经能够修复 bug 和开发功能，并常在 SWE-bench 上评估。然而 SWE-bench 只用 Python 仓库，问题陈述以文本为主，缺少图片等视觉元素。这促使我们研究：现有系统能否泛化到未覆盖的软件工程领域（如前端、游戏、DevOps），这些领域使用不同编程语言和范式？为此我们提出 **SWE-bench Multimodal（SWE-bench M）**，评估系统修复视觉化、用户-facing 的 JavaScript 软件中的 bug。SWE-bench M 包含 **617** 个任务实例，来自 **17** 个用于网页界面设计、图表、数据可视化、语法高亮和交互式地图的 JavaScript 库。每个任务的问题陈述或单元测试中至少包含一张图片。我们发现，顶级 SWE-bench 系统在 SWE-bench M 上表现糟糕，暴露出视觉问题解决和跨语言泛化的局限。最后，SWE-agent 的灵活、语言无关特性使其显著优于其他系统，解决率达到 **12%**，而次优系统仅为 **6%**。

**写作可借鉴点**：

- 首句直接点名前辈工作（SWE-bench）及其局限；
- 用问句形式抛出研究问题，与标题呼应；
- 给出新维度：视觉 + JavaScript + 跨语言泛化；
- 结果部分用“最顶尖系统也仅 12%”强调难度。

---

## 3. 引言（Introduction）框架

### 3.1 四段式结构

| 段落 | 功能 | 原文要点 |
|---|---|---|
| P1 | 背景 | LM 正从代码行/函数级助手，发展到维护大型代码库的自主系统。 |
| P2 | SWE-bench 成就 | 从 GitHub issue/PR 收集任务，已成为最流行 benchmark；Lite 子集 SOTA 从 3% 飙升到 43%。 |
| P3 | SWE-bench 局限 | 仅 Python、仓库结构同质化；缺乏 UI/游戏/VR/数据可视化等视觉领域。 |
| P4 | 研究问题 | “Do AI Systems Generalize to Visual Software Domains?” |
| P5-P6 | 提出 SWE-bench M | 619 个 JavaScript 任务，聚焦用户-facing 应用，强制包含图片/视频；人工验证 83.5% 的图片对解题必要。 |
| P7-P8 | 主要发现与启示 | 现有系统表现差；视觉元素类型多样；JavaScript 多范式增加难度；系统应更通用、语言无关、交互优先。 |

### 3.2 关键写作句式

- “SWE-bench reflects only a fraction of real-world applications.”
  → SWE-bench 只覆盖了真实应用场景的一小部分。
- “Many domains of software development rely on visual assets, such as user interface design, gaming, virtual reality, and data visualizations.”
  → 许多软件开发领域依赖视觉资产，如 UI 设计、游戏、VR、数据可视化。
- “Our efforts to adapt existing systems highlight generalizability as a desirable but overlooked consideration.”
  → 在适配现有系统时，我们发现“泛化能力”是一个被忽视但至关重要的设计目标。

### 3.3 图 1 描述

> 四个来自 SWE-bench Multimodal 的任务示例。JavaScript 仓库引入了新的软件开发挑战，如上图所示的用例，以及性能剖析、艺术编码等。除了多模态理解，SWE-bench M 还包含更多编程语言（JavaScript、TypeScript、HTML、CSS）和自然语言（英语、中文）的混合。

**对应 SD-HWE-Bench**：

- 图 1 可改为“ADL 工程中的多物理域设计增量示例”：电源、散热、结构、信号完整性。
- 强调“跨域”与“多模态约束”：不只是代码，还有物理方程、几何、材料、制造规则。

---

## 4. SWE-bench Multimodal 任务构建（第 2 节）

### 4.1 形式化定义（继承 SWE-bench）

- 每个任务对应一个 PR 与一个或多个 issue；
- issue 描述 bug 或功能请求；PR 包含解决方案代码和验证正确性的单元测试；
- 存在 fail-to-pass（F2P）测试：应用 patch 前失败、应用后通过；
- 存在 pass-to-pass（P2P）测试：验证已有功能未被破坏；
- 模型/智能体看到代码库 + issue，修改代码库使所有测试通过。

### 4.2 局限分析（Limitations）

1. **视觉缺失**：SWE-bench 96.4% 任务无图片；即使 5.6% 含图，也不知道图是否必要。
2. **语言单一**：仅 Python；未涉及 JavaScript 的异步、DOM/状态操作、web 开发范式。

### 4.3 五阶段数据收集流程

| 阶段 | 操作 | 规模 |
|---|---|---|
| 1 | 找用户-facing JS 仓库：≥5000 stars、≥500 PRs；人工选 17 个可视化相关库 | 17 repos |
| 2 | 过滤 issue/PR：问题描述或测试代码中含图片/视频链接 | 135k PRs → 1,478 候选 |
| 3 | 环境配置：添加 Node.js + Chrome，写安装/测试脚本；平均每个仓库耗时 10 小时 | 可运行 679 个实例 |
| 4 | 剔除不一致测试：同一 patch 运行 10 次，去掉结果不一致的测试 | 643 个实例 |
| 5 | 人工验证：判断图片类型与必要性；移除不可能任务 24 个 | 619 个最终实例 |

**写作可借鉴点**：

- 阶段 3 强调“环境搭建是最大人工成本”，这是 benchmark 论文常见痛点，值得详细写；
- 阶段 4 用“运行 10 次去噪”体现评测严谨性；
- 阶段 5 人工验证给出量化指标（83.5% 图片必要）。

### 4.4 Table 2 关键统计（中位数）

| 属性 | 中位数 |
|---|---|
| Issue 长度（词） | 105 |
| 代码库行数（非测试） | 549K |
| 代码库文件数（非测试） | 1,799 |
| Gold patch 编辑行数 | 27 |
| Gold patch 编辑文件数 | 2 |
| Gold patch 编辑函数数 | 3 |
| Fail-to-pass 测试数 | 1 |
| Pass-to-pass 测试数 | 5 |
| 图片宽高比 | 5:3 |
| 图片文件大小 | 42.95 KB |
| 图片分辨率 | 262K 像素 |

**与 SWE-bench 对比**：

- Issue 更短（105 vs. 195 词），但图片承载了额外信息；
- 编辑文件数更多（2 vs. 1.7），因为前端任务常涉及 HTML/CSS/TypeScript；
- 总测试数更少（中位数 6 vs. 130），但包含像素级视觉测试。

### 4.5 特性分析（Features）

1. **图片多样性**：862 张问题陈述图片，分为 7 类：
   - UI 截图（401）：布局/可访问性问题；
   - 代码截图（194）：将视觉线索映射到代码实体；
   - 错误信息图（54）；
   - 图表（107）、艺术图（38）、地图（35）、数据可视化（28）。
2. **多图/视频**：221 个实例含多图，70 个含视频；43 个来自 bpmn-js 用 GIF 展示交互。
3. **视觉测试**：69 个实例用像素级截图对比进行视觉测试。
4. **图片必要性**：80% 的问题陈述图片包含“超出文字本身的信息”；83.5% 的实例中图片对解题必要。
5. **难度曲线**：13% <15 分钟，43% 15 分钟–1 小时，38% 1–4 小时，6% >4 小时；平均比 SWE-bench 更难。

**对应 SD-HWE-Bench**：

- 我们任务的“视觉元素”可替换为“物理约束/仿真报告/几何图纸/网表截图”；
- 可设计“约束必要性”人工标注：多少任务必须看仿真波形/热图/几何图才能解；
- 可引入像素级/指标级视觉/数值测试。

---

## 5. 现有系统适配与实验（第 3 节）

### 5.1 适配发现：泛化能力被忽视

许多 SWE-bench 系统过度依赖 Python AST/静态分析工具，迁移到 JS 时要么重写，要么失效。

### 5.2 四个系统的适配情况

| 系统 | 原设计 | 适配结果 |
|---|---|---|
| **SWE-agent** | 轻量级 LM ↔ OS/shell 接口，文本 ACI |  easiest；只需支持图片输入和浏览器/截图工具；推出 SWE-agent Base / JS / M 三版。 |
| **Agentless** | localize-then-repair，用 Python ast | 需用 tree-sitter/自定义 JS parser 替换 ast；即使重写后开发集解决率仍 0%。 |
| **AutoCodeRover** | 两阶段：检索 + patch 生成，依赖 Python 程序分析 | 认为需要彻底重构，未评测。 |
| **Moatless** | AST → 可搜索代码图（Faiss） | JS/TS parser 不成熟，未评测。 |

### 5.3 实验设置

- **模型**：GPT-4o、Claude 3.5 Sonnet（需要长上下文 + 多模态 + 结构化输出）。
- **基线**：RAG、SWE-agent（Base/JS/M）、Agentless JS。
- **指标**：% Resolved（主指标）、Avg. $ Cost（平均每条推理成本）。

---

## 6. 结果与分析（第 4 节）

### 6.1 主结果 Table 3（已清洗）

| 系统 | 模型 | % Resolved | Avg. $ Cost |
|---|---|---|---|
| SWE-agent M | GPT-4o | 12.2 | $2.94 |
| SWE-agent M | Claude 3.5 Sonnet | 11.4 | $3.11 |
| SWE-agent JS | GPT-4o | 9.2 | $0.99 |
| SWE-agent JS | Claude 3.5 Sonnet | 12.0 | $3.11 |
| SWE-agent Base | GPT-4o | 12.0 | $2.07 |
| SWE-agent Base | Claude 3.5 Sonnet | 12.2 | $1.52 |
| Agentless JS | GPT-4o | 3.1 | $0.38 |
| Agentless JS | Claude 3.5 Sonnet | 6.2 | $0.42 |
| RAG | GPT-4o | 6.0 | $0.17 |
| RAG | Claude 3.5 Sonnet | 5.0 | $0.15 |

### 6.2 关键结论

1. **交互式 agent 显著优于固定流程**：SWE-agent 平均 11.5% vs. Agentless/RAG 的 3.9%/5.5%。
2. **JS/多模态定制收益不明显**：SWE-agent JS/M 与 Base 整体差异不大，说明核心瓶颈在 LM 本身。
3. **换模型影响小**：同一系统内 GPT-4o 与 Claude 3.5 Sonnet 差异不显著。
4. **图片必不可少**：去掉图片后，RAG/SWE-agent JS 性能显著下降（Table 4）。
5. **定位模块过度工程化**：Python AST 设计假设导致 Agentless JS 在 JS 上 F1 仅 0.142，而 SWE-agent 达 0.367。
6. **通用性启示**：未来系统应“LM-first + 交互工具”，而非把推理负担卸载给固定 pipeline。
7. **多模态工具双刃剑**：约 20% 动作用于截图/浏览；GPT-4o 正确提交率从无图的 10.4% 提升到 19.6%，但 Claude 上反而下降。

### 6.3 Table 4：有无图片对比（dev set）

| 系统 | 模型 | 有图片 | 无图片 |
|---|---|---|---|
| SWE-agent JS | GPT-4o | 11.0 | 8.0 |
| SWE-agent JS | Claude 3.5 Sonnet | 16.0 | 13.0 |
| RAG | GPT-4o | 10.0 | 8.0 |
| RAG | Claude 3.5 Sonnet | 14.1 | 11.2 |

### 6.4 对 SD-HWE-Bench 的启示

- **不要过度依赖语言专属静态分析**：ADL 是领域特定语言，但应避免把大量工程推理硬编码到 AST 解析器里；让 LM 在交互环境中自己探索。
- **交互式 agent 优于固定 pipeline**：SD-HWE-Bench 的 Actor 应支持多步工具调用（ESA 仿真、几何检查、约束求解）。
- **视觉/多模态输入可能是必要信号**：对硬件设计而言，仿真波形、热图、几何剖面、BOM 表、网表图都可能包含文字无法表达的信息。
- **成本与性能 trade-off**：报告 `% Resolved` 同时报告 `$ Cost`，对 benchmark 论文很有说服力。

---

## 7. 相关工作（第 5 节）写作策略

### 7.1 两个维度

| 维度 | 代表方向 | 作用 |
|---|---|---|
| 多模态代码 benchmark | HumanEval 饱和后，向多语言、多模态、数据科学、仓库理解、网络安全、效率等方向扩展 | 定位 SWE-bench M 是“软件工程 + 多模态代码生成”的交汇点。 |
| LM Agent for Web & Code | UI→前端代码、网页导航、软件工程 agent | 强调 SWE-bench M 首次把“网页/应用导航”与“软件工程”结合起来。 |

### 7.2 可借鉴写法

- 用“性能饱和”引出扩展方向；
- 把新工作放在两个已有方向的交汇点，显得既有继承又有创新；
- 用“to the best of our knowledge, the first benchmark that...”强化 novelty。

---

## 8. 结论（第 6 节）

> 本文提出 SWE-bench Multimodal（SWE-bench M），首个评估 coding agent 在真实软件工程任务中处理视觉元素的 benchmark。SWE-bench M 包含 619 个来自 17 个用户-facing JavaScript 仓库的任务，涵盖网页 UI 设计、数据可视化、艺术和地图。分析表明它包含多样化视觉挑战，任务复杂度高于 SWE-bench。现有系统表现不佳，最高解决率仅 12.2%；将多模态引入 SWE-bench 不仅扩展了令人兴奋的实用挑战，也鼓励从业者开发更通用、语言无关的解决方案，避免过拟合到 SWE-bench 或 Python 仓库。

**对应 SD-HWE-Bench**：

- 把“视觉元素”替换为“物理/工程约束与仿真反馈”；
- 把“Python 仓库”替换为“单一领域/单一工具链的 benchmark”；
- 把“语言无关”替换为“领域无关的可计算工程表示层（ADL）”。

---

## 9. 对 SD-HWE-Bench 论文写作的额外启示

| 维度 | SWE-bench Multimodal 做法 | SD-HWE-Bench 对应 |
|---|---|---|
| **标题** | 疑问句 + “Multimodal / Visual” | “Can LLM Agents Resolve Multiphysics Hardware Engineering Issues with Executable Digital Models?” |
| **卖点** | 跨语言（Python→JS）+ 跨模态（文本→图像） | 跨物理域 + 跨抽象层（行为/结构/约束）+ 可执行反馈 |
| **数据构建** | 五阶段 + 人工验证 + 环境搭建成本量化 | canonical 工程 → commit 提取 → ESA 环境搭建 → 不一致测试剔除 → 人工验证 |
| **对比表** | Table 1 与 RepoEval/RepoBench/SWE-bench 对比 | 与 HumanEval-EDA、Circuit-Bench、OpenROAD-flow 等对比 |
| **系统适配** | 详细写 Agentless/AutoCodeRover/Moatless 为何失败 | 可写传统 EDA 脚本/agent 为何无法直接迁移到 ADL |
| **成本指标** | 同时报告 % Resolved 与 $ Cost | 报告 pass@1 / cost / time / repair 轮数 |
| **失败分析** | 定位模块 F1、截图动作占比、正确提交率 | ESA 调用次数、仿真失败类型、约束违反分布 |
| **人工标注** | 图片必要性、图片类型、预计解决时间 | 约束必要性、任务类型、预计工程师解决时间 |

---

## 10. 可直接引用的关键数字

- 任务数：**619**（测试集 517，开发集 102）
- 仓库数：**17**（测试集 12，开发集 5）
- 问题陈述图片数：**862**
- 图片必要性：**83.5%** 实例中图片对解题必要
- 视觉测试实例：**69**
- 最高解决率：**12.2%**（SWE-agent M + GPT-4o）
- 次优系统：**6.2%**（Agentless JS + Claude 3.5 Sonnet）
- 平均每个仓库环境搭建时间：**10 小时**
