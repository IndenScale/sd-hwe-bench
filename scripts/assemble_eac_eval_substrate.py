#!/usr/bin/env python3
"""Assemble the EaC evaluation substrate Chinese paper from section files.

Usage:
  uv run scripts/assemble_eac_eval_substrate.py

Output:
  papers/engineering-as-code-eval-substrate/src/dist/draft-full.zh.md
"""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_DIR = REPO_ROOT / "papers/engineering-as-code-eval-substrate/src/sections-zh"
DIST_DIR = SECTIONS_DIR.parent / "dist"

SECTION_ORDER = [
    "01-introduction.md",
    "02-three-gaps.md",
    "03-testbed.md",
    "04-representation-experiment.md",
    "05-constraint-experiment.md",
    "06-knowledge-experiment.md",
    "07-related-work.md",
    "08-discussion.md",
    "09-limitations.md",
    "10-conclusion.md",
]


def demote_headings(markdown: str) -> str:
    """Demote section-fragment headings when assembling under one paper title."""
    output = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            output.append(f"#{line}")
        else:
            output.append(line)
    return "\n".join(output)


def main() -> None:
    meta = yaml.safe_load((SECTIONS_DIR / "meta.yaml").read_text())

    lines = [
        f"# {meta['title']}",
        "",
        f"> {meta['subtitle']}",
        "> 中文创作版 · 当前阶段：论述冻结与结果占位稿",
        "",
        "## 摘要",
        "",
        meta["abstract"].strip(),
        "",
        f"**关键词**：{', '.join(meta.get('keywords', []))}",
        "",
    ]

    for fname in SECTION_ORDER:
        fpath = SECTIONS_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing section: {fpath}")
        lines.append(demote_headings(fpath.read_text().strip()))
        lines.append("")

    appendix_dir = SECTIONS_DIR / "appendix"
    appendix_sections = sorted(appendix_dir.glob("*.md"))
    if appendix_sections:
        lines.extend(["---", "", "## 附录", ""])
        for fpath in appendix_sections:
            lines.append(demote_headings(fpath.read_text().strip()))
            lines.append("")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DIST_DIR / "draft-full.zh.md"
    output_text = "\n".join(lines)
    output_path.write_text(output_text)

    print(f"Done -> {output_path}")
    print(f"  Sections: {len(SECTION_ORDER)}")
    print(f"  Appendices: {len(appendix_sections)}")
    print(f"  Total lines: {len(output_text.splitlines())}")


if __name__ == "__main__":
    main()
