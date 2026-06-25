#!/usr/bin/env python3
"""Parse ar5iv HTML into a structured markdown outline."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    text = re.sub(r"\$\$.*?\$\$", "", text, flags=re.S)
    text = re.sub(r"\$.*?\$", "", text)
    text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", text)
    text = " ".join(text.split())
    return text


def parse_html(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    article = soup.find("article", class_="ltx_document") or soup.find("article")
    if not article:
        raise RuntimeError("No <article> found")

    title_tag = article.find("h1", class_="ltx_title_document") or article.find("h1")
    title = clean_text(title_tag.get_text()) if title_tag else ""

    authors = []
    for span in article.find_all("span", class_="ltx_personname"):
        authors.append(clean_text(span.get_text()))
    if not authors:
        for span in article.find_all("span", class_="ltx_author"):
            authors.append(clean_text(span.get_text()))

    abstract = ""
    abstract_tag = article.find("div", class_="ltx_abstract") or article.find("section", id="abstract")
    if abstract_tag:
        abstract = clean_text(abstract_tag.get_text())

    sections: list[dict] = []
    current_section: dict | None = None
    current_subsection: dict | None = None

    def add_paragraph(text: str):
        if current_subsection:
            current_subsection.setdefault("paragraphs", []).append(text)
        elif current_section:
            current_section.setdefault("paragraphs", []).append(text)
        elif sections:
            sections[-1].setdefault("paragraphs", []).append(text)

    def add_figcaption(text: str):
        container = current_subsection or current_section or (sections[-1] if sections else None)
        if container:
            container.setdefault("figures", []).append(text)

    def add_table(caption: str, rows: list[list[str]]):
        container = current_subsection or current_section or (sections[-1] if sections else None)
        if container:
            container.setdefault("tables", []).append({"caption": caption, "rows": rows})

    for elem in article.descendants:
        if getattr(elem, "name", None) is None:
            continue
        name = elem.name
        classes = " ".join(elem.get("class", []))

        if name in ("h1", "h2") and "ltx_title_section" in classes:
            current_section = {"title": clean_text(elem.get_text()), "paragraphs": [], "figures": [], "tables": []}
            current_subsection = None
            sections.append(current_section)
        elif name == "h3" and "ltx_title_subsection" in classes:
            current_subsection = {"title": clean_text(elem.get_text()), "paragraphs": [], "figures": [], "tables": []}
            if current_section is None:
                current_section = {"title": "", "paragraphs": [], "figures": [], "tables": []}
                sections.append(current_section)
            current_section.setdefault("subsections", []).append(current_subsection)
        elif name == "figcaption":
            add_figcaption(clean_text(elem.get_text()))
        elif name == "caption":
            continue  # handled in table parse
        elif name == "table":
            caption = ""
            cap = elem.find("caption")
            if cap:
                caption = clean_text(cap.get_text())
            rows = []
            for tr in elem.find_all("tr"):
                row = [clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
                if row:
                    rows.append(row)
            add_table(caption, rows)
        elif name == "p":
            txt = clean_text(elem.get_text())
            if txt:
                add_paragraph(txt)
        elif name == "li":
            txt = clean_text(elem.get_text())
            if txt:
                add_paragraph("- " + txt)

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "sections": sections,
    }


def to_markdown(data: dict) -> str:
    lines = [f"# {data['title']}", ""]
    if data["authors"]:
        lines.append(f"**Authors**: {', '.join(data['authors'])}")
        lines.append("")
    lines.append("## Abstract")
    lines.append(data["abstract"])
    lines.append("")
    for sec in data["sections"]:
        lines.append(f"## {sec['title']}")
        lines.append("")
        for p in sec.get("paragraphs", []):
            lines.append(p)
            lines.append("")
        for fig in sec.get("figures", []):
            lines.append(f"_Figure_: {fig}")
            lines.append("")
        for tbl in sec.get("tables", []):
            lines.append(f"_Table_: {tbl['caption']}")
            for row in tbl["rows"]:
                lines.append(" | ".join(row))
            lines.append("")
        for sub in sec.get("subsections", []):
            lines.append(f"### {sub['title']}")
            lines.append("")
            for p in sub.get("paragraphs", []):
                lines.append(p)
                lines.append("")
            for fig in sub.get("figures", []):
                lines.append(f"_Figure_: {fig}")
                lines.append("")
            for tbl in sub.get("tables", []):
                lines.append(f"_Table_: {tbl['caption']}")
                for row in tbl["rows"]:
                    lines.append(" | ".join(row))
                lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_ar5iv.py <html-file>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    data = parse_html(path)
    json_path = path.with_suffix(".json")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = path.with_suffix(".structured.md")
    md_path.write_text(to_markdown(data), encoding="utf-8")
    print(f"Wrote {json_path} and {md_path}")
