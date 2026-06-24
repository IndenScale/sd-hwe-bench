#!/usr/bin/env bash
# render-latex.sh — Markdown -> LaTeX -> PDF pipeline for arXiv/FSE submissions.
#
# Usage:
#   build/scripts/render-latex.sh [--lang zh|en]              # generate dist/latex/<slug>.tex
#   build/scripts/render-latex.sh [--lang zh|en] --pdf        # also compile PDF if a LaTeX engine is available
#   build/scripts/render-latex.sh [--lang zh|en] --anonymous  # omit author/affiliation metadata
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

PDF_MODE=false
ANONYMOUS=false
LANG="en"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pdf) PDF_MODE=true; shift ;;
    --anonymous) ANONYMOUS=true; shift ;;
    --lang)
      if [[ $# -lt 2 ]]; then
        echo "Missing argument for --lang"; exit 1
      fi
      LANG="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$LANG" == "zh" ]]; then
  SECTIONS_DIR="$PAPER_DIR/src/sections"
  TEMPLATE="$PAPER_DIR/build/templates/arxiv-zh.tex"
else
  SECTIONS_DIR="$PAPER_DIR/src/sections-en"
  TEMPLATE="$PAPER_DIR/build/templates/arxiv.tex"
fi

SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$SECTIONS_DIR")"

mkdir -p "$PAPER_DIR/dist/latex"

MD_FILE="$PAPER_DIR/dist/latex/${SLUG}-latex.md"
TEX_FILE="$PAPER_DIR/dist/latex/${SLUG}.tex"
PDF_FILE="$PAPER_DIR/dist/latex/${SLUG}.pdf"

echo "Assembling LaTeX-ready Markdown..."
bash "$SCRIPT_DIR/assemble-latex.sh" "$SECTIONS_DIR" "$MD_FILE"

METADATA_OVERRIDES=""
if [[ "$ANONYMOUS" == true ]]; then
  METADATA_OVERRIDES="--metadata=author:Anonymous --metadata=institute:"
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
  $METADATA_OVERRIDES

rm -f "$MD_FILE"

echo "Post-processing tables..."
python3 "$SCRIPT_DIR/fix-latex-tables.py" "$TEX_FILE"

if [[ "$PDF_MODE" == true ]]; then
  # Try to locate a TeX Live engine even if the shell PATH is not yet set.
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
    cd "$PAPER_DIR/dist/latex"
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$(basename "$TEX_FILE")" || true
    # Run twice to resolve references
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$(basename "$TEX_FILE")" || true
    cd "$PAPER_DIR"
  fi
fi

SIZE_KB=$(du -k "$TEX_FILE" | cut -f1)
echo "Done: $TEX_FILE (${SIZE_KB} KB)"

if [[ "$PDF_MODE" == true ]] && [[ -f "$PDF_FILE" ]]; then
  PDF_SIZE_KB=$(du -k "$PDF_FILE" | cut -f1)
  echo "Done: $PDF_FILE (${PDF_SIZE_KB} KB)"
fi
