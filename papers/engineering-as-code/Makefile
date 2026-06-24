.PHONY: md md-zh md-en pdf pdf-zh pdf-en pdf-zh-anonymous pdf-en-anonymous tex tex-zh tex-en tex-zh-anonymous tex-en-anonymous arxiv arxiv-pdf arxiv-anonymous arxiv-source arxiv-source-anonymous arxiv-source-verify all clean

md-zh:
	@bash build/scripts/assemble.sh

md-en:
	@bash build/scripts/assemble-en.sh

md: md-zh md-en

# HTML/Paged.js PDF pipeline
pdf-zh:
	@node build/scripts/render-pdf.js

pdf-en:
	@node build/scripts/render-pdf.js --en

pdf-zh-anonymous:
	@node build/scripts/render-pdf.js --anonymous

pdf-en-anonymous:
	@node build/scripts/render-pdf.js --en --anonymous

pdf: pdf-zh pdf-en

# LaTeX / arXiv / FSE pipeline
tex-zh:
	@bash build/scripts/render-latex.sh --lang zh

tex-en:
	@bash build/scripts/render-latex.sh --lang en

tex-zh-anonymous:
	@bash build/scripts/render-latex.sh --lang zh --anonymous

tex-en-anonymous:
	@bash build/scripts/render-latex.sh --lang en --anonymous

tex: tex-zh tex-en

arxiv: tex-en

arxiv-pdf:
	@bash build/scripts/render-latex.sh --lang en --pdf

arxiv-anonymous: tex-en-anonymous

arxiv-source:
	@bash build/scripts/prepare-arxiv-source.sh

arxiv-source-anonymous:
	@bash build/scripts/prepare-arxiv-source.sh --anonymous

arxiv-source-verify:
	@bash build/scripts/prepare-arxiv-source.sh --verify

all: md pdf tex

clean:
	@rm -rf dist/md dist/pdf dist/latex dist/submissions
	@rm -f .tmp-metadata.json .tmp-manuscript.html
	@echo "Cleaned build artifacts."
