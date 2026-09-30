# ¿A dónde va tu dinero? MTY — common tasks. Run `make help`.
.PHONY: help install data discover fetch build-data test e2e lint dev build image run check-headers clean

IMAGE ?= gdmty:dev

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install pipeline and web dependencies (from lockfiles)
	cd pipeline && uv sync --locked
	cd web && npm ci --ignore-scripts

discover: ## Look for new quarters and add them to pipeline/sources.yaml
	cd pipeline && uv run python -m gdmty discover

fetch: ## Download new source files (data/raw/)
	cd pipeline && uv run python -m gdmty fetch

build-data: ## Validate originals and generate data/public/v1/
	cd pipeline && uv run python -m gdmty build

data: discover fetch build-data ## discover + fetch + build-data

test: ## Pipeline and web tests
	cd pipeline && uv run pytest -q
	cd web && npm test

e2e: ## Browser tests against a running container (make image run in another terminal)
	cd web && npx playwright test

lint: ## Linters and type checks
	cd pipeline && uv run ruff check . && uv run ruff format --check .
	cd web && npm run lint && npm run check

dev: ## Dev server at http://localhost:5173
	cd web && npm run dev

build: ## Build the static site (web/dist)
	cd web && npm run build

image: ## Build the container image
	docker build -t $(IMAGE) .

run: ## Run the container hardened, as in production, at http://localhost:8080
	docker run --rm -p 8080:8080 --read-only --tmpfs /tmp --cap-drop ALL \
	  --security-opt no-new-privileges $(IMAGE)

check-headers: ## Check security headers against a running container
	sh scripts/check-headers.sh http://127.0.0.1:8080

clean: ## Remove build output
	rm -rf web/dist
