IMAGE := stylometry
PROVIDER ?= anthropic

.PHONY: build analyze shell clean

build:
	docker build -t $(IMAGE) .

# make analyze FILE=input/book.pdf
# make analyze FILE=input/book.pdf LLM=1
# make analyze URL=https://example.com/essay
# make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100
analyze: build
ifdef URL
	docker run --rm \
		-v $(CURDIR)/output:/output \
		$(if $(LLM),-e LLM_ENABLED=1 -e LLM_PROVIDER=$(PROVIDER) -e ANTHROPIC_API_KEY -e OPENAI_API_KEY,) \
		$(if $(CRAWL),-e CRAWL=1,) \
		$(if $(MAX_PAGES),-e MAX_PAGES=$(MAX_PAGES),) \
		$(IMAGE) "$(URL)"
else
ifndef FILE
	$(error Usage: make analyze FILE=input/book.pdf  (or)  make analyze URL=https://...)
endif
	docker run --rm \
		-v $(CURDIR)/input:/input \
		-v $(CURDIR)/output:/output \
		$(if $(LLM),-e LLM_ENABLED=1 -e LLM_PROVIDER=$(PROVIDER) -e ANTHROPIC_API_KEY -e OPENAI_API_KEY,) \
		$(IMAGE) "/input/$(notdir $(FILE))"
endif

shell: build
	docker run --rm -it \
		-v $(CURDIR)/input:/input \
		-v $(CURDIR)/output:/output \
		--entrypoint /bin/bash \
		$(IMAGE)

clean:
	rm -f output/*.html output/*.md
