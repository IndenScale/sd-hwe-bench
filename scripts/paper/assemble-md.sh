#!/usr/bin/env bash
# Assemble src/sections/*.md into a single Markdown file named after the title.
# Usage: assemble-md.sh [--sections-dir DIR] [--en] [output.md]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PAPER_DIR=""
SECTIONS_DIR=""
OUTPUT=""
LANG="zh"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --paper-dir)
      if [[ $# -lt 2 ]]; then echo "Missing argument for --paper-dir"; exit 1; fi
      PAPER_DIR="$2"; shift 2 ;;
    --paper-dir=*) PAPER_DIR="${1#*=}"; shift ;;
    --sections-dir)
      if [[ $# -lt 2 ]]; then echo "Missing argument for --sections-dir"; exit 1; fi
      SECTIONS_DIR="$2"; shift 2 ;;
    --sections-dir=*) SECTIONS_DIR="${1#*=}"; shift ;;
    --en) LANG="en"; shift ;;
    -*)
      echo "Unknown option: $1"; exit 1 ;;
    *)
      OUTPUT="$1"; shift ;;
  esac
done

if [[ -n "$PAPER_DIR" ]]; then
  SECTIONS_DIR="${SECTIONS_DIR:-$PAPER_DIR/src/sections}"
  if [[ "$LANG" == "en" ]]; then
    SECTIONS_DIR="$PAPER_DIR/src/sections-en"
  fi
fi

if [[ -z "$SECTIONS_DIR" ]]; then
  echo "ERROR: --paper-dir or --sections-dir is required" >&2
  exit 1
fi

if [[ ! -d "$SECTIONS_DIR" ]]; then
  echo "ERROR: sections dir not found: $SECTIONS_DIR" >&2
  exit 1
fi

SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$SECTIONS_DIR")"

if [[ -z "$OUTPUT" ]]; then
  if [[ -n "$PAPER_DIR" ]]; then
    OUTPUT="$PAPER_DIR/dist/$SLUG.md"
  else
    echo "ERROR: --paper-dir is required when output is not specified" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$OUTPUT")"

python3 - "$SECTIONS_DIR" "$OUTPUT" "$LANG" << 'PYEOF'
import sys, os, re
import yaml

sections_dir, output, lang = sys.argv[1], sys.argv[2], sys.argv[3]

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
parts.extend(['---', '', ''])
result.extend(parts)

# Collect all markdown files: numbered sections first, then appendix/
section_files = sorted(
    f for f in os.listdir(sections_dir)
    if f.endswith('.md') and f != 'meta.yaml' and not f.startswith('.')
)
appendix_dir = os.path.join(sections_dir, 'appendix')
appendix_files = []
if os.path.isdir(appendix_dir):
    appendix_files = sorted(
        f for f in os.listdir(appendix_dir)
        if f.endswith('.md') and not f.startswith('.')
    )

all_files = section_files + [f'appendix/{f}' for f in appendix_files]

for fname in all_files:
    if fname.startswith('appendix/'):
        path = os.path.join(sections_dir, fname)
    else:
        path = os.path.join(sections_dir, fname)

    if not os.path.isfile(path):
        continue

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines or not lines[0].startswith('# '):
        sys.exit(f'ERROR: {path} must start with "# Title"')
    section_title = lines[0][2:].strip()

    result.append(f'## {section_title}')
    result.append('')  # blank line after heading

    idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    for line in lines[idx:]:
        result.append(promote(line).rstrip('\n'))

    result.append('')

# Assemble and post-process: ensure blank lines around headings
text = '\n'.join(result)

# Fix MD022: headings should be surrounded by blank lines.
# A heading line (## or ### ...) not preceded by a blank line gets one inserted.
text = re.sub(r'([^\n])\n(#{2,6}\s)', r'\1\n\n\2', text)
# Fix MD024: deduplicate identical H3 headings in appendix by appending section names
# This is a cosmetic fix — the real fix is in the source files.

with open(output, 'w', encoding='utf-8') as f:
    f.write(text)

total_lines = text.count('\n') + 1
print(f'Assembled markdown -> {output}')
print(f'  Sections: {len(all_files)}')
print(f'  Lines:    {total_lines}')
PYEOF
