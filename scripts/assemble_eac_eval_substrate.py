#!/usr/bin/env python3
"""Assemble the EaC evaluation substrate Chinese paper from section files.

Usage:
  uv run scripts/assemble_eac_eval_substrate.py

Output:
  papers/engineering-as-code-eval-substrate/src/dist/draft-full.zh.md
"""

from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_SRC_DIR = REPO_ROOT / "papers/engineering-as-code-eval-substrate/src"
SECTIONS_DIR = PAPER_SRC_DIR / "sections-zh"
TEMPLATES_DIR = PAPER_SRC_DIR / "templates"
DATA_DIR = PAPER_SRC_DIR / "data"
DIST_DIR = PAPER_SRC_DIR / "dist"

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
    "11-references.md",
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


def load_yaml(path: Path) -> dict:
    """Load a YAML file, treating an empty file as an empty mapping."""
    data = yaml.safe_load(path.read_text())
    return data or {}


def load_paper_data() -> dict:
    """Load Jinja data available to all section templates."""
    data = {}
    for path in sorted(DATA_DIR.glob("*.yaml")):
        data[path.stem.replace("-", "_")] = load_yaml(path)
    return data


def render_markdown_template(env: Environment, markdown: str, *, meta: dict, data: dict) -> str:
    """Render a section markdown fragment as a Jinja template."""
    return env.from_string(markdown).render(meta=meta, data=data)


def main() -> None:
    meta = load_yaml(SECTIONS_DIR / "meta.yaml")
    data = load_paper_data()

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    sections = []
    for fname in SECTION_ORDER:
        fpath = SECTIONS_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing section: {fpath}")
        rendered = render_markdown_template(
            env,
            fpath.read_text().strip(),
            meta=meta,
            data=data,
        )
        sections.append(
            {
                "filename": fname,
                "content": demote_headings(rendered),
            }
        )

    appendix_dir = SECTIONS_DIR / "appendix"
    appendix_sections = [
        {
            "filename": fpath.name,
            "content": demote_headings(
                render_markdown_template(
                    env,
                    fpath.read_text().strip(),
                    meta=meta,
                    data=data,
                )
            ),
        }
        for fpath in sorted(appendix_dir.glob("*.md"))
    ]
    template = env.get_template("draft-full.zh.md.j2")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DIST_DIR / "draft-full.zh.md"
    output_text = template.render(
        meta=meta,
        stage="中文创作版 · 当前阶段：论述冻结与结果占位稿",
        keywords=", ".join(meta.get("keywords", [])),
        data=data,
        sections=sections,
        appendix_sections=appendix_sections,
    )
    output_path.write_text(output_text)

    print(f"Done -> {output_path}")
    print(f"  Sections: {len(SECTION_ORDER)}")
    print(f"  Appendices: {len(appendix_sections)}")
    print(f"  Total lines: {len(output_text.splitlines())}")


if __name__ == "__main__":
    main()
