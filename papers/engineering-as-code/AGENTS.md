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

### 叙事策略

- **对手不是 ACC/BIM/CAD**，而是「物理工程缺乏 source code 表示」这一空缺本身。
- **竞争范式对比**：ACC（事后下游检查）vs. ESA（事前设计时检查）——timing difference 是核心论证。
- **SE 工具链 mapping**：ADL ↔ DSL design，ESA ↔ compiler/linter pipeline，EPM ↔ package manager，Git workflow ↔ VCS。
- **RLVR 因果链**：结构化可验证表示 → 毫秒级确定性反馈 → RLVR 训练有效 → Agent 能力跃迁。论文论证的是第一环（表示层），不是第四环（Agent）。

### 投稿策略（2026-06-21 更新）

### 首选：FSE 2027 Research Track

- 18+4 页，允许完整展开 DSL 设计、static analysis 架构、分层验证和初步实证。
- FSE 2027 明确将 "Artificial intelligence and machine learning for software engineering" 列入 Topics of Interest。
- 投稿截止：2026-10-02。

论证口径：本文解决的是 **SE 基础设施设计问题**（如何为没有 source code 的领域设计 source code 表示层）。物理工程是案例，不是贡献本体。SE 审稿人应该关心 ADL 的 DSL 设计决策、ESA 的分层静态分析架构、以及「表示层设计如何使能下游 AI 训练」这一因果链条。

**备选路径：**

- **ICSE 2028 Research Track**（若 FSE 被拒）：更广的 SE 受众，更长的审稿周期。
- **OOPSLA Onward! 2027**：偏 radical vision，适合较短篇幅。
- 不投 AEC/engineering 期刊——本文是 SE 贡献，投 AEC 期刊会丢失 SE 社区话语权。

## 文件结构

```text
papers/engineering-as-code/
├── AGENTS.md                        # 本文件
├── sections/                         # FSE Research Track 正文（真相源，按节拆分）
│   ├── 00-abstract.md
│   ├── 01-introduction.md
│   ├── 02-background.md
│   ├── 03-the-eac-approach.md
│   ├── 04-adl.md
│   ├── 05-esa.md
│   ├── 06-evaluation.md
│   ├── 07-related-work.md
│   └── 08-conclusion.md
├── appendix/                         # 扩展/参考材料
│   ├── 01-concept-eac/
│   ├── 02-language-adl/
│   ├── 03-shift-left-quality/
│   ├── 04-infrastructure/
│   └── 05-future-ai4engineering/
├── references/                       # 已下载的参考文献 PDF
├── refs.bib
├── engineering-as-code.zh.md         # 【已废弃】旧版中文全文稿
└── engineering-as-code.en.md         # 【已废弃】旧版英文全文稿
```

## 写作语言与术语

1. **`sections/` 是投稿真相源**：按 FSE Research Track 结构直接用英文撰写。
2. **`appendix/` 采用 _zh / _en 双版本**：`_zh.md` 为中文原生创作版，`_en.md` 为英文投稿版。
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
| `lightman2024letsverify` | Let's Verify Step by Step       | §3         | PRM > ORM → step-level verifiability 是 RLVR 使能条件 |
| `sweagent2025swerl`      | SWE-RL                          | §3, §7     | 代码修复 RLVR 实证 → 验证信号必要性的证据点           |
| `chiari2024iacstatic`    | IaC Static Analysis (EMSE 2024) | §5, §7     | IaC 工具实证 → "X as Code" 静态分析可行且高效的先例   |
| `liu2023ifcversion`      | IFC Normalization for VC        | §2, §7     | IFC 无法 Git diff → CAD/BIM 不适合作为 code 表示的实证 |
| `mirhoseini2020rlchip`   | Chip Placement with Deep RL     | §2, §3     | RL+netlist+DRC → 解耦表示是 RL 训练前提               |

### 当前引用统计

- refs.bib: 28 条
- 已下载 PDF: 15 篇
- sections/ 正文引用点: 待统计
