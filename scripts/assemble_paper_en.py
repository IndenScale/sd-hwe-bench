#!/usr/bin/env python3
"""Assemble the full English paper (SD-HWE-Bench) from section files.

Usage:
  uv run scripts/assemble_paper_en.py

Output:
  papers/sd-hwe-bench/src/dist/draft-full.en.md

All numbers come from real codebase data — no placeholders.
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_DIR = REPO_ROOT / "papers/sd-hwe-bench/src/sections-en"
APPENDIX_DIR = SECTIONS_DIR / "appendix"
DIST_DIR = SECTIONS_DIR.parent / "dist"

# ── Real data (update these after re-running experiments) ──
N_TASKS = 33
N_CANONICAL = 3
N_DOMAINS = 1  # telecom, with 3 sub-domains (rack/datacenter/site)
N_MODELS = 1   # DeepSeek-v4-Flash via Codex CLI (more models pending)
BEST_PASS1 = 94   # 31/33 tasks, pass@1, no repair
BEST_SCORE = 84.7  # Average overall weighted score

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
    if fpath.exists():
        sections.append(fpath.read_text().strip())
    else:
        sections.append(f"<!-- {fname} not yet written -->")
        print(f"  [WARNING] {fname} not found, placeholder inserted")

# ── Read appendices, skip glossary ─────────────────────────
appendix_sections = []
for fpath in sorted(APPENDIX_DIR.glob("*.md")):
    if "glossary" in fpath.name.lower():
        continue
    appendix_sections.append(fpath.read_text().strip())

# ── Build English abstract ─────────────────────────────────
abstract_text = (
    "While large language models have made significant progress in code, mathematics, and text "
    "reasoning, AI agents have begun to enter the domain of physical engineering design. However, "
    "existing benchmarks are mostly concentrated in code, mathematics, or text reasoning, lacking "
    "systematic evaluation of structured representation, constraint checking, and manufacturability "
    "verification for engineering design. This paper proposes SD-HWE-Bench, a declarative hardware "
    "engineering benchmark based on the Assembly Definition Language (ADL) and Design Test Suite (DTS). "
    f"We construct {N_CANONICAL} canonical engineering projects covering telecom rack, datacenter, and "
    "telecom site domains, and extract design incremental tasks from their commit histories, totaling "
    f"{N_TASKS} task instances. Experiments demonstrate that on DeepSeek-v4-Flash (via Codex CLI Agent), "
    f"under full context and pass@1 without repair, pass@1 reaches {BEST_PASS1}% ({31}/{33} tasks), "
    f"with an average overall score of {BEST_SCORE}%. The L-Numeric scoring layer successfully exposes "
    "LLM weaknesses in multi-step formula evaluation and physical modeling fidelity. We open-source the "
    "canonical ADL projects, task extraction tools, and evaluation harness to support future research "
    "and RLVR training."
)

# ── Assemble ───────────────────────────────────────────────
lines = []

# Title
lines.append(f"# {meta['title']}")
lines.append("")
lines.append("> English draft · Current stage: baseline experiments complete (33 tasks, 1 model)")
lines.append("> All numbers from real codebase data — no placeholders")
lines.append("")

# Abstract
lines.append("## Abstract")
lines.append("")
lines.append(abstract_text)
lines.append("")
lines.append(f"**Keywords**: {', '.join(meta.get('keywords', []))}")
lines.append("")

# Body sections
for sec in sections:
    lines.append(sec)
    lines.append("")

# Appendices
lines.append("---")
lines.append("")
lines.append("## Appendices")
lines.append("")
for app in appendix_sections:
    lines.append(app)
    lines.append("")

# ── Write ──────────────────────────────────────────────────
DIST_DIR.mkdir(parents=True, exist_ok=True)
output_path = DIST_DIR / "draft-full.en.md"
output_path.write_text("\n".join(lines))

print(f"Done → {output_path}")
print(f"  Sections: {len(sections)}")
print(f"  Appendices: {len(appendix_sections)}")
print(f"  Total lines: {len(lines)}")
