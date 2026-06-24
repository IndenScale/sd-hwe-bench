#!/usr/bin/env bash
# Assemble a sections directory into an arXiv/FSE-ready LaTeX source pipeline.
# Outputs a single Markdown file with a YAML metadata block followed by body sections.
#
# Usage: build/scripts/assemble-latex.sh <sections_dir> [output.md]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

SECTIONS_DIR="${1:-$PAPER_DIR/arxiv/src/sections-en}"
SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$SECTIONS_DIR")"
OUTPUT="${2:-$PAPER_DIR/dist/latex/${SLUG}-latex.md}"
mkdir -p "$(dirname "$OUTPUT")"

python3 - "$SECTIONS_DIR" "$OUTPUT" << 'PYEOF'
import sys, os, re
import yaml

sections_dir, output = sys.argv[1], sys.argv[2]

def promote(line: str) -> str:
    m = re.match(r'^(#{1,6})\s', line)
    if not m:
        return line
    level = len(m.group(1))
    if level >= 6:
        return line
    return '#' * (level + 1) + line[level:]

meta_path = os.path.join(sections_dir, 'meta.yaml')
if not os.path.isfile(meta_path):
    sys.exit(f'ERROR: missing {meta_path}')

with open(meta_path, 'r', encoding='utf-8') as f:
    meta = yaml.safe_load(f) or {}

parts = ['---']
for key in ('title', 'author', 'institute'):
    val = meta.get(key)
    if val:
        parts.append(f'{key}: "{val}"')
abstract = meta.get('abstract', '')
if abstract:
    parts.append('abstract: |')
    for line in str(abstract).splitlines():
        parts.append('  ' + line)
keywords = meta.get('keywords', '')
if keywords:
    parts.append(f'keywords: "{keywords}"')
parts.extend(['---', ''])

files = sorted(
    f for f in os.listdir(sections_dir)
    if f.endswith('.md') and f != 'meta.yaml'
)

for fname in files:
    path = os.path.join(sections_dir, fname)
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    parts.append(text.rstrip('\n'))
    parts.append('')
    parts.append('')

with open(output, 'w', encoding='utf-8') as f:
    f.write('\n'.join(parts))

print(f'Assembled LaTeX markdown -> {output}')
print(f'  Sections: {len(files)}')
print(f'  Title:    {meta.get("title", "")}')
print(f'  Author:   {meta.get("author", "")}')
PYEOF
