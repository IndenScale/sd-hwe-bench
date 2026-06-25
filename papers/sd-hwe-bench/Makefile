.PHONY: md md-zh md-en clean

REPO_ROOT := $(shell cd ../../ && pwd)
SCRIPT_DIR := $(REPO_ROOT)/scripts/paper
PAPER_DIR := $(REPO_ROOT)/papers/sd-hwe-bench

md-zh:
	@bash $(SCRIPT_DIR)/assemble-md.sh \
		--sections-dir $(PAPER_DIR)/src/sections-zh \
		$(PAPER_DIR)/dist/sd-hwe-bench.zh.md

md-en:
	@bash $(SCRIPT_DIR)/assemble-md.sh \
		--sections-dir $(PAPER_DIR)/src/sections-en \
		$(PAPER_DIR)/dist/sd-hwe-bench.en.md

md: md-zh md-en

clean:
	@rm -rf $(PAPER_DIR)/dist
	@echo "Cleaned $(PAPER_DIR)/dist"
