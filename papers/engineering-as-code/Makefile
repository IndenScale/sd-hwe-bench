.PHONY: md md-zh md-en pdf pdf-zh pdf-en pdf-zh-anonymous pdf-en-anonymous tex tex-zh tex-en tex-zh-anonymous tex-en-anonymous arxiv arxiv-pdf arxiv-anonymous arxiv-source arxiv-source-anonymous arxiv-source-verify fse fse-zh fse-md fse-md-zh fse-md-en fse-tex fse-tex-anonymous fse-tex-zh fse-tex-zh-anonymous fse-pdf fse-pdf-anonymous fse-pdf-zh fse-pdf-zh-anonymous all clean

md-zh:
	@bash build/scripts/assemble.sh

md-en:
	@bash build/scripts/assemble-en.sh

md: md-zh md-en

# FSE Markdown assembly
fse-md-zh:
	@bash build/scripts/assemble.sh --sections-dir fse/src/sections "fse/dist/md-zh/$$(python3 build/scripts/slug-from-meta.py fse/src/sections).md"

fse-md-en:
	@bash build/scripts/assemble-en.sh --sections-dir fse/src/sections-en "fse/dist/md/$$(python3 build/scripts/slug-from-meta.py fse/src/sections-en).md"

fse-md: fse-md-zh fse-md-en

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

# FSE 2027 submission pipeline
fse-tex:
	@bash build/scripts/render-fse-latex.sh

fse-tex-anonymous:
	@bash build/scripts/render-fse-latex.sh --anonymous

fse-pdf:
	@bash build/scripts/render-fse-latex.sh --pdf

fse-pdf-anonymous:
	@bash build/scripts/render-fse-latex.sh --pdf --anonymous

fse-tex-zh:
	@bash build/scripts/render-fse-latex.sh --lang zh

fse-pdf-zh:
	@bash build/scripts/render-fse-latex.sh --lang zh --pdf

fse-tex-zh-anonymous:
	@bash build/scripts/render-fse-latex.sh --lang zh --anonymous

fse-pdf-zh-anonymous:
	@bash build/scripts/render-fse-latex.sh --lang zh --pdf --anonymous

fse-zh: fse-tex-zh

fse: fse-tex

all: md pdf tex fse-md fse-tex fse-tex-zh

clean:
	@rm -rf arxiv/dist fse/dist
	@rm -f .tmp-metadata.json .tmp-manuscript.html
	@echo "Cleaned build artifacts."
