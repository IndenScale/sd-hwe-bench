# Engineering as Code 论文开发说明

## 论文定位

本文是一篇面向 **软件工程（SE）社区** 的 Position Paper / Vision Paper。核心命题不是「AI 能在物理工程 work」，而是：

> **当一个领域还没有 source code 的时候，软件工程社区应该怎么去为它设计 source code？**

论文将 EaC 定位为 **SE 基础设施向新领域的外推**（移植 DSL 设计、静态分析、版本控制语义、CI/CD 管线和包管理范式到物理工程领域），而非「AI 工程应用」或「AI for physical engineering」。

### 为什么投 SE 会

ADL 不是机械设计语言——它是让物理设计获得 code-like 属性（可 parse、可 diff、可版本化、可静态分析、可 LSP 诊断）的 **软件抽象设计问题**。
ESA 不是建筑规范检查器——它是把 compiler/linter/pre-commit hook 范式移植到物理约束领域的 **通用 static analysis 框架**。
EPM / AssemblyHub 不是工程协作工具——它们是让 physical design 获得软件式可组合性和可复用性的 **包管理与协作基础设施**。

这些全都是 SE 社区的老本行。本文论证的正是：**物理工程领域需要一个 SE 式的表示层和工具链，而设计这个表示层本身就是 SE 研究问题**。目标领域（telecom rack / datacenter / mechanical keyboard）只是案例，不是贡献本体。

### 核心贡献（投稿陈述口径）

1. **ADL: Assembly Definition Language**：三层正交、text-native 设计语言（PDL/PML/PLL），设计为 SE 工具链的 *design surface*——YAML-based（可 parse）、orthogonal（每层独立 checkable）、diff-friendly（支持 Git-based design review 和 branching）。

2. **ESA: Engineering Static Analysis**：确定性分层规则引擎（L0–L4），将合规检查从下游 audit 前移到 pre-commit design-time gating，直接类比 compiler analysis pipeline（syntax → reference integrity → business rules → geometric constraints）。ESA 提供毫秒级 pass/fail 反馈，可作为 RLVR 训练信号。

3. **Information Representation Hypothesis**：可测试的理论锚点——AI 在物理工程的瓶颈是缺少可计算设计表示，而非模型能力/物理复杂度。将 EaC 技术选择（ADL + ESA）连接到 RLVR 因果链。

## 当前状态（2026-06-24）

| 维度 | 状态 |
|---|---|
| ADL / ESA 概念与实现 | 清晰，3 samples 全过，违规注入 15/15 检出 |
| Agent 实证 | 刚完成 5 telecom tasks × 2 actors 的 pass@1 smoke：Kimi 80%、DeepSeek-v4-pro 20% |
| 基础设施 | SD-HWE-Bench 跑通：评分器、repair loop、归档、测试 49/49 绿 |
| 容器化 | Docker 未运行，当前 `--sandbox none`，需尽快固化 |
| 论文写作 | 仅 MEMO 与章节草稿，未形成 FSE Vision Track 投稿稿 |

## 下一步（未来 2 周）

1. **验证 prompt 修改效果**：重跑 instance-declare / deliverable 任务，确认 Kimi 稳定提升。
2. **补最小 ablation**：no-repair vs repair，5 tasks × 1 actor × 3 passes，支撑 Information Representation Hypothesis。
3. **启动 container 环境**：构建 `sd-hwe-bench-piki` image，确保评分可复现。
4. **确定 FSE Vision Track 论文大纲**：基于现有章节草稿，整理出投稿版结构。
5. **评估 AI benchmark track 可行性**：SD-HWE-Bench 的目标是 NeurIPS / ICLR 等 AI 会议的 Dataset/Benchmark Track。若 8 月中旬前任务无法扩展到 12–15 个并完成多模型基线，则推迟到下一个周期。

### 叙事策略

- **对手不是 ACC/BIM/CAD**，而是「物理工程缺乏 source code 表示」这一空缺本身。
- **竞争范式对比**：ACC（事后下游检查）vs. ESA（事前设计时检查）——timing difference 是核心论证。
- **SE 工具链 mapping**：ADL ↔ DSL design，ESA ↔ compiler/linter pipeline，EPM ↔ package manager，Git workflow ↔ VCS。
- **RLVR 因果链**：结构化可验证表示 → 毫秒级确定性反馈 → RLVR 训练有效 → Agent 能力跃迁。论文论证的是第一环（表示层），不是第四环（Agent）。

### 投稿策略（2026-06-24 更新）

本文拆分为两个独立投稿目标：

#### 目标 A：FSE 2027 Vision Track（本仓库 `fse/`）

- **定位**：Position / Vision Paper，面向 SE 社区提出 Engineering as Code 研究议程。
- **核心命题**：当一个领域还没有 source code 时，SE 社区如何为它设计可计算表示层。
- **篇幅与格式**：按 FSE 2027 Vision Track 要求（通常短于 Research Track，具体以 CFP 为准）。
- **论证口径**：本文解决的是 **SE 基础设施设计问题**（DSL、static analysis、VCS-like design review）。物理工程是案例，不是贡献本体。SE 审稿人应关心 ADL 的 DSL 设计决策、ESA 的分层静态分析架构、以及「表示层设计如何使能下游 AI 训练」这一因果链条。
- **实验要求**：足以支撑愿景即可，不追求完整 benchmark。当前 smoke 结果（Kimi 80% pass@1、ESA feedback 初步有效）可作为 feasibility demonstration。
- **投稿截止**：2026-10-02。

#### 目标 B：AI 会议 Dataset / Benchmark Track（`papers/sd-hwe-bench.zh/`）

- **定位**：SD-HWE-Bench 数据集/基准论文，面向 AI 社区，证明工程 AI 需要结构化表示和 ESA 反馈。
- **目标会议推荐**：
  - **首选：NeurIPS 2027 Evaluations & Datasets Track**（截稿约 2027-05）。最匹配：NeurIPS E&D 接收新 benchmark、评估方法论和 AI4Science 数据集；更名后的 track 强调“evaluation as scientific study”，与我们的 no-repair vs repair ablation、错误模式分析高度契合。时间也最充裕，可以从容扩展任务和多模型基线。
  - **冲刺选项：ICLR 2027 Datasets & Benchmarks Track**（截稿约 2026-09/10）。如果能在 8 月底前把任务扩展到 12–15 个、跑完 3–4 个模型基线并完成 ablation，可以尝试；否则风险过高。
  - **稳妥选项：ICML 2027 Datasets Track**（截稿约 2027-01）。时间和声望都适中，若 ICLR 赶不上可自然转投。
- **核心贡献**：任务集、评价协议、多模型基线结果、复现包、错误模式分析。
- **当前差距**：仅 5 个 telecom 任务、host-only 环境、2 个 Actor 基线。要达到 AI benchmark track 的可信度，需要扩展任务、容器化、3–4 个模型 pass@k、完整 ablation。
- **决策点**：8 月中旬前若无法扩展到 12–15 个任务并完成多模型实验，则放弃 ICLR 冲刺，以 NeurIPS 2027 为主目标。

**备选路径（Vision Track 若被拒）：**

- **ICSE 2028 Research / Vision Track**：更广的 SE 受众。
- **OOPSLA Onward! 2027**：偏 radical vision，适合较短篇幅。
- **arXiv 预印本**：建立优先权，同时投后续 venue。
- 不投 AEC/engineering 期刊——本文是 SE 贡献，投 AEC 期刊会丢失 SE 社区话语权。

## 文件结构

```text
papers/engineering-as-code/
├── AGENTS.md                         # 本文件
├── Makefile                          # 构建入口
├── refs.bib                          # BibTeX 引用单真相源
├── arxiv/                            # arXiv 投稿真相源（完整版）
│   └── src/
│       ├── sections/                 # 中文正文源文件
│       ├── sections-en/              # 英文正文源文件
│       └── appendix/                 # 扩展/参考材料
├── fse/                              # FSE 2027 投稿真相源（精简版）
│   └── src/
│       ├── sections/                 # 中文正文源文件
│       ├── sections-en/              # 英文正文源文件（18 页目标）
│       └── appendix/                 # FSE 附录（+4 页）
├── assets/                           # 静态资产
│   ├── diagrams/                     # 论文插图
│   └── references/                   # 已下载的参考文献 PDF
├── build/                            # 构建脚本与模板
│   ├── scripts/                      # 构建脚本
│   │   ├── assemble.sh               # Markdown 合并（中文）
│   │   ├── assemble-en.sh            # Markdown 合并（英文 arXiv）
│   │   ├── assemble-latex.sh         # Markdown 合并（LaTeX 投稿源）
│   │   ├── render-pdf.js             # Markdown -> HTML -> PDF
│   │   ├── render-latex.sh           # Markdown -> LaTeX -> PDF（arXiv）
│   │   ├── render-fse-latex.sh       # Markdown -> LaTeX -> PDF（FSE）
│   │   ├── fix-latex-tables.py       # LaTeX 表格后处理
│   │   ├── slug-from-meta.py         # 从 meta.yaml 标题生成文件名
│   │   └── prepare-arxiv-source.sh   # 打包 arXiv 源文件 tar.gz
│   └── templates/                    # Pandoc 模板
│       ├── arxiv.tex                 # 英文 LaTeX 模板（arXiv）
│       ├── arxiv-zh.tex              # 中文 LaTeX 模板
│       ├── fse.tex                   # ACM acmart 模板（FSE）
│       ├── fse-anonymous.tex         # ACM 匿名审稿模板（FSE）
│       └── arxiv-template.html       # HTML/PDF 模板
└── dist/                             # 所有下游产物（gitignored）
    ├── md/                           # 合并后的单一 Markdown 文件
    ├── pdf/                           # HTML/Paged.js PDF
    ├── latex/                        # LaTeX 源（arXiv）
    ├── fse/latex/                    # LaTeX 源 + PDF（FSE）
    └── submissions/                  # 各出版渠道投稿包
        ├── arxiv/
        └── arxiv-anonymous/
```

**命名规则**：下游产物文件名从 `meta.yaml` 的 `title` 自动派生（slug），不再使用 `manuscript` 等硬编码名称。

**核心原则**：`arxiv/src/`、`fse/src/` 与 `assets/` 是**唯一可编辑的真相源**；`dist/` 是**完全生成的下游产物**，可随时 `make clean` 重建。
## 构建管线

### LaTeX 投稿源（arXiv / FSE 首选）

```bash
# 生成 dist/latex/<slug>.tex（本地无需 LaTeX）
make tex-en

# 中文 LaTeX 源
make tex-zh

# 若已安装 TeX Live / MacTeX，同时编译 PDF
make arxiv-pdf

# 匿名版本（审稿用）
make tex-en-anonymous

# 生成可直接上传 arXiv 的源文件包（tar.gz）
make arxiv-source

# 匿名版源文件包
make arxiv-source-anonymous

# 打包并本地编译验证（需 TeX Live / MacTeX）
make arxiv-source-verify
```

该管线：
- 从 `arxiv/src/sections-en/meta.yaml` / `arxiv/src/sections/meta.yaml` 提取 `\title` / `\author` / `\affil` / `\begin{abstract}` / keywords。
- 章节文件（`01-introduction.md` 等）只包含正文，不再包含标题页或摘要。
- 使用 `pandoc-crossref` 处理图表交叉引用，`pandoc-citeproc` + `refs.bib` 生成 BibTeX 参考文献。
- 章节标题不再手写编号，由 LaTeX `\section`/ `\subsection` 自动编号。
- 代码块使用 Pandoc 默认语法高亮，表格使用 `longtable` + `\caption`。

### Markdown / PDF

```bash
make md            # dist/md/<zh-slug>.md + dist/md/<en-slug>.md
make md-zh
make md-en
make pdf           # dist/pdf/<zh-slug>.pdf + dist/pdf/<en-slug>.pdf
make pdf-zh
make pdf-en
make pdf-zh-anonymous
make pdf-en-anonymous
```

## 写作语言与术语

1. **`arxiv/src/sections-en/` 是 arXiv 投稿真相源**：完整版 Position Paper。
2. **`fse/src/sections-en/` 是 FSE 投稿真相源**：精简版（目标 18+4 页）。
3. **`arxiv/src/appendix/` 采用 _zh / _en 双版本**：`_zh.md` 为中文原生创作版，`_en.md` 为英文投稿版。
3. 旧版 `engineering-as-code.zh.md` / `engineering-as-code.en.md` 已废弃，不再维护。

## 写作风格

- **审稿人友好**：每节开头 1-2 句点明「本节的核心 takeaway」。
- **对比驱动**：ACC vs. ESA、SysML v2 vs. ADL、BIM/IFC vs. Design-as-Code 是贯穿全文的叙事暗线。
- **可测试声称**：信息表示假说必须表述为 SD-HWE-Bench 可验证的预测。
- **最小化缩写密度**：同一段中避免连续出现 3 个以上新缩写。
- **SE 社区口语**：使用 SE 审稿人熟悉的词汇——DSL design、static analysis pipeline、pre-commit gating、diagnostic format、RLVR reward signal——而非工程领域的 CAD/BIM 行话为主。

## 引用管理

引用格式为 Pandoc/BibTeX `[@键名]` 格式。`refs.bib` 是单真相源。

### 关键 bridge 文献（强化论证链条）

| 键名                     | 论文                            | 论证位置   | 作用                                                  |
| ------------------------ | ------------------------------- | ---------- | ----------------------------------------------------- |
| `lightman2023letsverify` | Let's Verify Step by Step       | §3         | PRM > ORM → step-level verifiability 是 RLVR 使能条件 |
| `sweagent2025swerl`      | SWE-RL                          | §3, §7     | 代码修复 RLVR 实证 → 验证信号必要性的证据点           |
| `chiari2024iacstatic`    | IaC Static Analysis (EMSE 2024) | §5, §7     | IaC 工具实证 → "X as Code" 静态分析可行且高效的先例   |
| `liu2023ifcversion`      | IFC Normalization for VC        | §2, §7     | IFC 无法 Git diff → CAD/BIM 不适合作为 code 表示的实证 |
| `mirhoseini2020rlchip`   | Chip Placement with Deep RL     | §2, §3     | RL+netlist+DRC → 解耦表示是 RL 训练前提               |

### 当前引用统计

- refs.bib: 28 条
- 已下载 PDF: 15 篇
- sections/ 正文引用点: 待统计
