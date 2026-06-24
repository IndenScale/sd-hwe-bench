#!/usr/bin/env bash
# prepare-arxiv-source.sh — Package the LaTeX source for arXiv upload.
#
# Usage:
#   build/scripts/prepare-arxiv-source.sh              # non-anonymous source bundle
#   build/scripts/prepare-arxiv-source.sh --anonymous  # anonymous source bundle
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PAPER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

ANONYMOUS=false
VERIFY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --anonymous) ANONYMOUS=true; shift ;;
    --verify)    VERIFY=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$ANONYMOUS" == true ]]; then
  UPLOAD_DIR="$PAPER_DIR/dist/submissions/arxiv-anonymous"
  TARBALL="$PAPER_DIR/dist/submissions/arxiv-anonymous/arxiv-source-anonymous.tar.gz"
else
  UPLOAD_DIR="$PAPER_DIR/dist/submissions/arxiv"
  TARBALL="$PAPER_DIR/dist/submissions/arxiv/arxiv-source.tar.gz"
fi
SOURCE_DIR="$PAPER_DIR/dist/latex"
SLUG="$(python3 "$SCRIPT_DIR/slug-from-meta.py" "$PAPER_DIR/src/sections-en")"
TEX_FILE="${SLUG}.tex"

echo "=== Step 1: clean arXiv upload directory ==="
cd "$PAPER_DIR"
rm -rf "$UPLOAD_DIR"
mkdir -p "$UPLOAD_DIR"

echo "=== Step 2: generate LaTeX source ==="
if [[ "$ANONYMOUS" == true ]]; then
  make tex-en-anonymous >/dev/null
else
  make tex-en >/dev/null
fi

if [[ ! -f "$SOURCE_DIR/$TEX_FILE" ]]; then
  echo "ERROR: $SOURCE_DIR/$TEX_FILE was not generated."
  exit 1
fi

echo "=== Step 3: copy source files to upload directory ==="
cp "$SOURCE_DIR/$TEX_FILE" "$UPLOAD_DIR/"

# Auto-copy any figures referenced by \includegraphics in the .tex file.
# Search for both \includegraphics[...]{path} and \includegraphics{path}.
FIGURES="$(grep -oE '\\includegraphics(\[[^]]*\])?\{[^}]+\}' "$SOURCE_DIR/$TEX_FILE" 2>/dev/null \
  | sed -E 's/\\includegraphics(\[[^]]*\])?\{([^}]+)\}/\2/' \
  | sed -E 's/\.[^.]+$//' \
  | sort -u || true)"

if [[ -n "$FIGURES" ]]; then
  FIGURE_COUNT="$(echo "$FIGURES" | wc -l | tr -d ' ')"
  echo "Found $FIGURE_COUNT figure reference(s):"
  while IFS= read -r stem; do
    [[ -z "$stem" ]] && continue
    echo "  - $stem"
    found=false
    for ext in pdf png eps jpg jpeg; do
      candidate="$PAPER_DIR/assets/diagrams/${stem}.${ext}"
      if [[ -f "$candidate" ]]; then
        cp "$candidate" "$UPLOAD_DIR/"
        echo "    copied ${stem}.${ext}"
        found=true
        break
      fi
    done
    if [[ "$found" == false ]]; then
      echo "  WARNING: no image file found for '$stem' (looked in diagrams/)"
    fi
  done <<< "$FIGURES"
else
  echo "No \includegraphics references found in the manuscript."
fi

# Remove auxiliary files if the latex run left any in the upload dir.
rm -f "$UPLOAD_DIR"/*.aux "$UPLOAD_DIR"/*.log "$UPLOAD_DIR"/*.out "$UPLOAD_DIR"/*.bbl "$UPLOAD_DIR"/*.blg

echo "=== Step 4: optional local compilation check ==="
if [[ "$VERIFY" == true ]]; then
  ENGINE=""
  for candidate in pdflatex xelatex lualatex; do
    if command -v "$candidate" >/dev/null 2>&1; then
      ENGINE="$candidate"
      break
    fi
  done

  if [[ -z "$ENGINE" ]]; then
    echo "WARNING: no LaTeX engine found (pdflatex/xelatex/lualatex). Skipping verification."
    echo "Install MacTeX or TeX Live to enable --verify."
  else
    echo "Verifying with $ENGINE..."
    cd "$UPLOAD_DIR"
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$TEX_FILE" >/dev/null || true
    "$ENGINE" -interaction=nonstopmode -halt-on-error "$TEX_FILE" >/dev/null || true
    if [[ -f "${TEX_FILE%.tex}.pdf" ]]; then
      echo "Verification passed: PDF generated with $ENGINE."
      rm -f "${TEX_FILE%.tex}.pdf"
    else
      echo "WARNING: PDF was not generated. Check the .log file for errors."
    fi
    cd "$PAPER_DIR"
  fi
else
  echo "Skipping local verification (use --verify to compile with pdflatex/xelatex)."
fi

echo "=== Step 5: create arXiv source tarball ==="
rm -f "$TARBALL"
TARBALL_TMP="$(mktemp -u "$PAPER_DIR/.arxiv-source-XXXXXX.tar.gz")"
trap 'rm -f "$TARBALL_TMP"' EXIT
cd "$PAPER_DIR"
tar -czvf "$TARBALL_TMP" -C "$UPLOAD_DIR" .
mv "$TARBALL_TMP" "$TARBALL"
trap - EXIT

echo ""
echo "Done. arXiv source bundle:"
echo "  $TARBALL"
echo ""
echo "Upload contents:"
ls -la "$UPLOAD_DIR"
