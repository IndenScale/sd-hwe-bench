#!/usr/bin/env python3
"""Assemble the full Chinese paper (SD-HWE-Bench) from section files.

Usage:
  uv run scripts/assemble_paper.py

Output:
  papers/sd-hwe-bench/src/dist/draft-full.zh.md

All numbers come from real codebase data — no [N_MODELS]/[BEST_PASS@1] placeholders.
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_DIR = REPO_ROOT / "papers/sd-hwe-bench/src/sections-zh"
DIST_DIR = SECTIONS_DIR.parent / "dist"

# ── Real data (update these after re-running experiments) ──
N_DATASET_TASKS = 37      # total tasks in tasks/telecom/
N_EVAL_TASKS = 28         # tasks with current pass@1 experiments (excluding new AIDC tasks)
N_CANONICAL = 5           # telecom-rack / datacenter / telecom-site / datacenter-hall / aidc-60mw (concept→detailed→epc lineage)
N_DOMAINS = 4             # rack, datacenter, telecom-site, AIDC
N_MODELS = 2              # Kimi k2.7, DeepSeek-v4-Pro via CLI
BEST_PASS1 = 87.1         # Kimi k2.7, pass@1, no repair (122/140)
BEST_SCORE = 82.7         # Kimi k2.7, average weighted score

# ── Load meta ──────────────────────────────────────────────
meta = yaml.safe_load((SECTIONS_DIR / "meta.yaml").read_text())

# ── Section order ──────────────────────────────────────────
SECTION_ORDER = [
    "01-introduction.md",
    "02-related-work.md",
    "03-benchmark-design.md",
    "04-dataset.md",
    "05-evaluation-protocol.md",
    "06-baselines.md",
    "07-ablation.md",
    "08-analysis.md",
    "09-limitations.md",
    "10-conclusion.md",
]

# ── Read sections ──────────────────────────────────────────
sections = []
for fname in SECTION_ORDER:
    fpath = SECTIONS_DIR / fname
    sections.append(
        fpath.read_text().strip() if fpath.exists()
        else f"<!-- {fname} not yet written -->"
    )

# Read appendices, skip glossary
appendix_dir = SECTIONS_DIR / "appendix"
appendix_sections = []
for fpath in sorted(appendix_dir.glob("*.md")):
    if "glossary" in fpath.name.lower():
        continue
    appendix_sections.append(fpath.read_text().strip())

# ── Assemble ───────────────────────────────────────────────
lines = []

# Title
lines.append(f"# {meta['title']}")
lines.append("")
lines.append("> 中文创作版 · 当前阶段：基线实验完成（28/37 tasks, 2 models）；4 个新 AIDC 任务参考方案已验证，多模型实验待补充")
lines.append("> 所有数字来自代码库实测，无占位符")
lines.append("")

# Abstract
lines.append("## 摘要")
lines.append("")
lines.append(
    "人工智能在科学、数学与代码领域已取得显著进展，但物理工程（Hardware Engineering）"
    "作为现代社会基础设施的核心，其智能化进程却明显滞后。工程领域是一个「确定性奖励稠密」的场景："
    "每个设计决策都可以通过规则检查、仿真或测试获得快速、明确的反馈，非常适合强化学习与可验证生成。"
    "然而，硬件工程仍受困于表示碎片化、商业 GUI 软件、昂贵仿真以及训练/评估基础设施不匹配等问题。"
)
lines.append("")
lines.append(
    "本文提出 **SD-HWE-Bench**，首个面向声明式硬件工程的大规模可执行 benchmark。"
    "我们采用 **Engineering as Code（EaC）** 思想，通过领域特定语言 **ADL** 将电源、热、结构、"
    "信号完整性等多物理域设计统一为可计算文本表示，并配套 **DTS（Design Test Suite）** "
    "分层确定性评分引擎，使 Agent 能在毫秒到秒级获得从语法（L0）、语义（L1）、引用完整性（L2）、"
    "装配体静态分析（L3）、动态分析（L4）到几何干涉与施工可建性（L5）的多层反馈，L6 预留为 FEM/CFD 等高精度仿真。"
    f"任务从精心构建的 {N_CANONICAL} 个 canonical 工程的 commit 历史中提取，"
    f"数据集共 {N_DATASET_TASKS} 个任务实例，覆盖电信机柜、数据中心、户外基站与 AIDC 四个子领域。"
)
lines.append("")
lines.append(
    f"我们在 SD-HWE-Bench 上评测了 Kimi k2.7 与 DeepSeek-v4-Pro（均通过 CLI Agent）。"
    f"在完整上下文、pass@1、无 repair 设置下，{N_EVAL_TASKS} 个已评测任务的当前最佳 pass@1 为 **{BEST_PASS1}%**，"
    f"最佳平均加权得分为 **{BEST_SCORE}%**。跨专业综合任务（telecom-cross-001）和 60MW AIDC "
    f"概念设计-调度联合优化任务（aidc-60mw-001）构成了当前主要的区分度来源。"
    f"此外，v7 新增的 detailed-design 与 epc 任务将施工可建性与 CPML 排程纳入评测，以拓展长程优化与工程建造维度。"
    f"我们开源了 canonical ADL 工程、任务提取工具与评测 harness，以支持后续研究与 RLVR 训练。"
)
lines.append("")
lines.append(f"**关键词**：{', '.join(meta.get('keywords', []))}")
lines.append("")

# Body
for sec in sections:
    lines.append(sec)
    lines.append("")

# Appendices
lines.append("---")
lines.append("")
lines.append("## 附录")
lines.append("")
for app in appendix_sections:
    lines.append(app)
    lines.append("")

# ── Write ──────────────────────────────────────────────────
DIST_DIR.mkdir(parents=True, exist_ok=True)
output_path = DIST_DIR / "draft-full.zh.md"
output_path.write_text("\n".join(lines))

print(f"Done → {output_path}")
print(f"  Sections: {len(sections)}")
print(f"  Appendices: {len(appendix_sections)}")
print(f"  Total lines: {len(lines)}")
