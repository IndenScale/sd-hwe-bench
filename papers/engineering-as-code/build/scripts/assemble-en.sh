#!/usr/bin/env bash
# Assemble src/sections-en/*.md into a single Markdown file named after the title.
# Usage: build/scripts/assemble-en.sh [--sections-dir DIR] [output.md]
# Default sections dir: arxiv/src/sections-en
# Default output: arxiv/dist/md/<slug>.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

SECTIONS_DIR="$PAPER_DIR/arxiv/src/sections-en"
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sections-dir)
      if [[ $# -lt 2 ]]; then echo "Missing argument for --sections-dir"; exit 1; fi
      SECTIONS_DIR="$2"; shift 2 ;;
    --sections-dir=*) SECTIONS_DIR="${1#*=}"; shift ;;
    -*)
      echo "Unknown option: $1"; exit 1 ;;
    *)
      OUTPUT="$1"; shift ;;
  esac
done

SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$SECTIONS_DIR")"
OUTPUT="${OUTPUT:-$PAPER_DIR/arxiv/dist/md/${SLUG}.md}"
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

result = []
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
result.extend(parts)

files = sorted(
    f for f in os.listdir(sections_dir)
    if f.endswith('.md') and f != 'meta.yaml'
)

for fname in files:
    path = os.path.join(sections_dir, fname)
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines or not lines[0].startswith('# '):
        sys.exit(f'ERROR: {path} must start with "# Title"')
    section_title = lines[0][2:].strip()

    result.append(f'## {section_title}')

    idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    for line in lines[idx:]:
        result.append(promote(line).rstrip('\n'))

    result.append('')

with open(output, 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

total_lines = sum(1 for l in result if l.strip())
print(f'Assembled markdown -> {output}')
print(f'  Sections: {len(files)}')
print(f'  Lines:    {total_lines}')
PYEOF
