#!/usr/bin/env bash
# render-fse-latex.sh — Markdown -> LaTeX -> PDF pipeline for FSE 2027 submissions.
#
# Usage:
#   build/scripts/render-fse-latex.sh [--lang zh|en] [--sections-dir DIR] [--pdf] [--anonymous]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

LANG="en"
PDF_MODE=false
ANONYMOUS=false
SECTIONS_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang)
      if [[ $# -lt 2 ]]; then echo "Missing argument for --lang"; exit 1; fi
      LANG="$2"; shift 2 ;;
    --sections-dir)
      if [[ $# -lt 2 ]]; then echo "Missing argument for --sections-dir"; exit 1; fi
      SECTIONS_DIR="$2"; shift 2 ;;
    --pdf) PDF_MODE=true; shift ;;
    --anonymous) ANONYMOUS=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$LANG" == "zh" ]]; then
  SECTIONS_DIR="${SECTIONS_DIR:-$PAPER_DIR/fse/src/sections}"
  if [[ "$ANONYMOUS" == true ]]; then
    TEMPLATE="$PAPER_DIR/build/templates/fse-zh-anonymous.tex"
  else
    TEMPLATE="$PAPER_DIR/build/templates/fse-zh.tex"
  fi
  OUTDIR="$PAPER_DIR/fse/dist/latex-zh"
  FSE_TABLE_MODE=true
else
  SECTIONS_DIR="${SECTIONS_DIR:-$PAPER_DIR/fse/src/sections-en}"
  if [[ "$ANONYMOUS" == true ]]; then
    TEMPLATE="$PAPER_DIR/build/templates/fse-anonymous.tex"
  else
    TEMPLATE="$PAPER_DIR/build/templates/fse.tex"
  fi
  OUTDIR="$PAPER_DIR/fse/dist/latex"
  FSE_TABLE_MODE=true
fi

SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$SECTIONS_DIR")"

mkdir -p "$OUTDIR"

MD_FILE="$OUTDIR/${SLUG}-latex.md"
TEX_FILE="$OUTDIR/${SLUG}.tex"
PDF_FILE="$OUTDIR/${SLUG}.pdf"

echo "Assembling LaTeX-ready Markdown..."
bash "$SCRIPT_DIR/assemble-latex.sh" "$SECTIONS_DIR" "$MD_FILE"

METADATA_OVERRIDES=""
if [[ "$ANONYMOUS" == true ]]; then
  METADATA_OVERRIDES="--metadata=author:Anonymous --metadata=institute:"
fi

LUA_FILTER_ARG=""
if [[ "$FSE_TABLE_MODE" == true ]]; then
  LUA_FILTER_ARG="--lua-filter=$PAPER_DIR/build/filters/tables-to-fse.lua"
fi

echo "Pandoc -> LaTeX..."
# shellcheck disable=SC2086
pandoc "$MD_FILE" \
  -o "$TEX_FILE" \
  --standalone \
  --template="$TEMPLATE" \
  --filter pandoc-crossref \
  --metadata=crossrefYaml:"$PAPER_DIR/.crossref.yaml" \
  --citeproc \
  --bibliography="$PAPER_DIR/refs.bib" \
  --top-level-division=section \
  --number-sections \
  --columns=1000 \
  $LUA_FILTER_ARG \
  $METADATA_OVERRIDES

rm -f "$MD_FILE"

echo "Post-processing tables..."
if [[ "$FSE_TABLE_MODE" != true ]]; then
  python3 "$SCRIPT_DIR/fix-latex-tables.py" "$TEX_FILE"
fi

if [[ "$PDF_MODE" == true ]]; then
  TEXLIVE_BIN=""
  for candidate in \
    /Library/TeX/texbin \
    /usr/local/texlive/2026/bin/universal-darwin \
    /usr/local/texlive/2025/bin/universal-darwin \
    /usr/local/texlive/2024/bin/universal-darwin \
    /opt/homebrew/bin; do
    if [[ -x "$candidate/xelatex" ]]; then
      TEXLIVE_BIN="$candidate"
      break
    fi
  done
  if [[ -n "$TEXLIVE_BIN" ]]; then
    export PATH="$TEXLIVE_BIN:$PATH"
  fi

  if command -v xelatex >/dev/null 2>&1; then
    ENGINE=xelatex
  elif command -v pdflatex >/dev/null 2>&1; then
    ENGINE=pdflatex
  else
    echo "WARNING: No LaTeX engine found (xelatex/pdflatex). Skipping PDF compilation."
    echo "Install TeX Live / MacTeX, then rerun with --pdf."
    PDF_MODE=false
  fi

  if [[ "$PDF_MODE" == true ]]; then
    echo "Compiling PDF with $ENGINE..."
    cd "$OUTDIR"
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$TEX_FILE" || true
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$TEX_FILE" || true
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$TEX_FILE" || true
    cd "$PAPER_DIR"
  fi
fi

SIZE_KB=$(du -k "$TEX_FILE" | cut -f1)
echo "Done: $TEX_FILE (${SIZE_KB} KB)"

if [[ "$PDF_MODE" == true ]] && [[ -f "$PDF_FILE" ]]; then
  PDF_SIZE_KB=$(du -k "$PDF_FILE" | cut -f1)
  echo "Done: $PDF_FILE (${PDF_SIZE_KB} KB)"
fi
