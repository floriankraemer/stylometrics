IMAGE := stylometry
PROVIDER ?= anthropic
# run as the host user so files written to bind mounts are not root-owned
RUN := docker run --rm --user $(shell id -u):$(shell id -g)
# rebuild only when the build inputs change, or the image is gone
STAMP := .build/image.stamp
BUILD_INPUTS := Dockerfile requirements.txt $(shell find src -name '*.py')
IMAGE_MISSING = $(shell docker image inspect $(IMAGE) >/dev/null 2>&1 || echo FORCE)

.DEFAULT_GOAL := help
.PHONY: help build analyze examples test serve binary shell clean FORCE

##@ General

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "\nUsage:\n  make \033[36m<target>\033[0m [VAR=value]\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)
	@printf "\nExamples:\n  make analyze FILE=input/book.pdf LLM=1\n  make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100\n\n"

##@ Build

build: ## Force a rebuild of the Docker image
	@rm -f $(STAMP) && $(MAKE) --no-print-directory $(STAMP)

$(STAMP): $(BUILD_INPUTS) $(IMAGE_MISSING)
	docker build -t $(IMAGE) .
	@mkdir -p $(dir $@) && touch $@

# make analyze FILE=input/book.pdf
# make analyze FILE=input/book.pdf LLM=1
# make analyze URL=https://example.com/essay
# make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100
##@ Analysis

analyze: $(STAMP) ## Analyze FILE=... or URL=... (opt: LLM=1 PROVIDER= CRAWL=1 MAX_PAGES=)
ifdef URL
	$(RUN) \
		-v $(CURDIR)/output:/output \
		$(if $(LLM),-e LLM_ENABLED=1 -e LLM_PROVIDER=$(PROVIDER) -e ANTHROPIC_API_KEY -e OPENAI_API_KEY,) \
		$(if $(CRAWL),-e CRAWL=1,) \
		$(if $(MAX_PAGES),-e MAX_PAGES=$(MAX_PAGES),) \
		$(IMAGE) "$(URL)"
else
ifndef FILE
	$(error Usage: make analyze FILE=input/book.pdf  (or)  make analyze URL=https://...)
endif
	$(RUN) \
		-v $(CURDIR)/input:/input \
		-v $(CURDIR)/output:/output \
		$(if $(LLM),-e LLM_ENABLED=1 -e LLM_PROVIDER=$(PROVIDER) -e ANTHROPIC_API_KEY -e OPENAI_API_KEY,) \
		$(IMAGE) "/input/$(notdir $(FILE))"
endif

# Re-run the analysis for every examples/<name>/<text>.txt into examples/<name>/output/
examples: $(STAMP) ## Re-run analysis for all examples/*/*.txt
	for f in examples/*/*.txt; do \
		d=$$(dirname $$f); mkdir -p $$d/output; \
		$(RUN) -v $(CURDIR)/$$d:/input:ro -v $(CURDIR)/$$d/output:/output $(IMAGE) /input/$$(basename $$f) || exit 1; \
	done

##@ Development

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

test: ## Run tests with coverage (needs requirements-dev.txt installed; fails under 80%)
	$(PYTHON) -m pytest

serve: ## Run the HTTP API locally (PORT=8000 HOST=127.0.0.1)
	$(PYTHON) -m stylometry.cli --serve --host $(or $(HOST),127.0.0.1) --port $(or $(PORT),8000)

binary: ## Build a native binary into dist/stylometry/ with PyInstaller
	$(PYTHON) -m PyInstaller --noconfirm packaging/stylometry.spec

shell: $(STAMP) ## Open a bash shell in the container
	$(RUN) -it \
		-v $(CURDIR)/input:/input \
		-v $(CURDIR)/output:/output \
		--entrypoint /bin/bash \
		$(IMAGE)

clean: ## Remove generated output/*.html and output/*.md
	rm -f output/*.html output/*.md
