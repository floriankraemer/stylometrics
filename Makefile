IMAGE := stylometry
PROVIDER ?= anthropic
# run as the host user so files written to bind mounts are not root-owned
RUN := docker run --rm --user $(shell id -u):$(shell id -g)

.DEFAULT_GOAL := help
.PHONY: help build analyze examples test shell clean

##@ General

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "\nUsage:\n  make \033[36m<target>\033[0m [VAR=value]\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)
	@printf "\nExamples:\n  make analyze FILE=input/book.pdf LLM=1\n  make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100\n\n"

##@ Build

build: ## Build the Docker image
	docker build -t $(IMAGE) .

# make analyze FILE=input/book.pdf
# make analyze FILE=input/book.pdf LLM=1
# make analyze URL=https://example.com/essay
# make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100
##@ Analysis

analyze: build ## Analyze FILE=... or URL=... (opt: LLM=1 PROVIDER= CRAWL=1 MAX_PAGES=)
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
examples: build ## Re-run analysis for all examples/*/*.txt
	for f in examples/*/*.txt; do \
		d=$$(dirname $$f); mkdir -p $$d/output; \
		$(RUN) -v $(CURDIR)/$$d:/input:ro -v $(CURDIR)/$$d/output:/output $(IMAGE) /input/$$(basename $$f) || exit 1; \
	done

##@ Development

test: build ## Run unit tests in the container
	$(RUN) -v $(CURDIR)/tests:/app/tests:ro --entrypoint python $(IMAGE) -m unittest discover -s /app/tests -v

shell: build ## Open a bash shell in the container
	$(RUN) -it \
		-v $(CURDIR)/input:/input \
		-v $(CURDIR)/output:/output \
		--entrypoint /bin/bash \
		$(IMAGE)

clean: ## Remove generated output/*.html and output/*.md
	rm -f output/*.html output/*.md
