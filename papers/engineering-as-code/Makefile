.PHONY: pdf pdf-en pdf-anonymous pdf-en-anonymous md md-en tex tex-en arxiv arxiv-pdf arxiv-anonymous arxiv-source arxiv-source-anonymous clean

md:
	@bash scripts/assemble.sh

md-en:
	@bash scripts/assemble-en.sh

# HTML/Paged.js PDF pipeline (legacy; good for visual drafts)
pdf:
	@node scripts/render-pdf.js

pdf-en:
	@node scripts/render-pdf.js --en

pdf-anonymous:
	@node scripts/render-pdf.js --anonymous

pdf-en-anonymous:
	@node scripts/render-pdf.js --en --anonymous

# LaTeX / arXiv pipeline (preferred for submission)
tex-en:
	@bash scripts/render-latex.sh

tex-en-anonymous:
	@bash scripts/render-latex.sh --anonymous

arxiv: tex-en

arxiv-pdf:
	@bash scripts/render-latex.sh --pdf

arxiv-anonymous:
	@bash scripts/render-latex.sh --anonymous

arxiv-source:
	@bash scripts/prepare-arxiv-source.sh

arxiv-source-anonymous:
	@bash scripts/prepare-arxiv-source.sh --anonymous

all: pdf pdf-anonymous pdf-en pdf-en-anonymous tex-en

clean:
	@rm -f manuscript.pdf manuscript-anonymous.pdf manuscript-en.pdf manuscript-en-anonymous.pdf manuscript-en-latex.md .tmp-metadata.json .tmp-manuscript.html
	@rm -f arxiv-submission/manuscript-en.tex arxiv-submission/manuscript-en.pdf arxiv-submission/*.aux arxiv-submission/*.log arxiv-submission/*.out arxiv-submission/*.bbl arxiv-submission/*.blg
	@rm -rf arxiv-upload
	@rm -f arxiv-source.tar.gz arxiv-source-anonymous.tar.gz
	@echo "Cleaned build artifacts."
