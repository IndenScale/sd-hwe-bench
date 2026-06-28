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

## 当前状态（2026-06-25）

| 维度 | 状态 |
|---|---|
| ADL / ESA 概念与实现 | 清晰，3 samples 全过，违规注入 15/15 检出 |
| Agent 实证 | Kimi POC 5 tasks pass@1=100%（avg 91%）；DeepSeek-v4-pro 20% |
| 基础设施 | SD-HWE-Bench 跑通：评分器、repair loop、归档、测试 90/90 绿 |
| 容器化 | ✅ Docker image 已构建（1.58GB），`scripts/build-piki-image.sh` 可重建 |
| 论文写作 | arXiv 完整版 PDF 已生成（173KB）+ tar.gz 投稿包；FSE Vision Track 缩写版待做 |

## 下一步

1. **FSE Vision Track 缩写**：从 arXiv 完整版缩至 FSE 版面（目标 18+4 页）
2. **补充 ablation 实验**：no-repair vs repair，19 tasks × Kimi × pass@5，支撑 Information Representation Hypothesis
3. **匿名化准备**：FSE 双盲审稿版

## 投稿策略

### 目标 A：FSE 2027 Vision Track（首选）

- **定位**：Position / Vision Paper，面向 SE 社区提出 Engineering as Code 研究议程。
- **核心命题**：当一个领域还没有 source code 时，SE 社区如何为它设计可计算表示层。
- **论证口径**：本文解决的是 **SE 基础设施设计问题**（DSL、static analysis、VCS-like design review）。物理工程是案例，不是贡献本体。

### 目标 B：arXiv 预印本（兜底）

- arXiv 完整版已生成 PDF 和 tar.gz 投稿包，位于 `arxiv/dist/submissions/arxiv/`。
- 若 FSE 被拒，直接上 arXiv + 转投其他 SE 刊物（ICSE NIER / ASE / Automation in Construction / JCISE）。

## 构建管线

真相源：`arxiv/src/sections-en/meta.yaml` + `arxiv/src/sections-en/*.md` + `arxiv/src/appendix/*.md`。

```bash
make tex-en                 # LaTeX 源
make arxiv-pdf              # LaTeX → PDF（需 MacTeX）
make arxiv-source            # arXiv tar.gz
```

产物都在 `dist/` 下，可随时 `make clean` 重建。

## 写作语言与术语

1. `arxiv/src/sections-en/` 是 arXiv 投稿真相源（完整版 Position Paper）。
2. `arxiv/src/appendix/` 采用 _zh /_en 双版本。
3. 术语：EaC（Engineering as Code）、ADL（三层子语言：PDL/PML/PLL）、ESA（L0-L4 分层静态分析）、EPM/AssemblyHub（包管理与协作）。不再使用 SDE、X-CCA、X-DRC。

## 引用管理

引用格式为 Pandoc/BibTeX `[@键名]` 格式。`refs.bib` 是单真相源（28 条，已下载 15 篇 PDF）。

### 关键 bridge 文献

| 键名 | 论文 | 论证位置 | 作用 |
|---|---|---|---|
| `lightman2023letsverify` | Let's Verify Step by Step | §3 | PRM > ORM → step-level verifiability 是 RLVR 使能条件 |
| `sweagent2025swerl` | SWE-RL | §3, §7 | 代码修复 RLVR 实证 → 验证信号必要性的证据点 |
| `chiari2024iacstatic` | IaC Static Analysis (EMSE 2024) | §5, §7 | IaC 工具实证 → "X as Code" 静态分析可行且高效的先例 |
| `liu2023ifcversion` | IFC Normalization for VC | §2, §7 | IFC 无法 Git diff → CAD/BIM 不适合作为 code 表示的实证 |
| `mirhoseini2020rlchip` | Chip Placement with Deep RL | §2, §3 | RL+netlist+DRC → 解耦表示是 RL 训练前提 |
