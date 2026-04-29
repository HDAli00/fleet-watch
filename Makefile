SHELL := /bin/bash
.DEFAULT_GOAL := help

ROOT := $(abspath $(CURDIR))
COMPOSE := docker compose -f app/docker-compose.yml --project-directory app
API_DIR := app/api
WEB_DIR := app/web

.PHONY: help setup lint typecheck test prebuild build up down logs migrate smoke check verify clean

help: ## List available targets
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

prebuild: ## Stage host CA bundle for docker build (TLS-intercepting envs)
	@if [ -f /etc/ssl/certs/ca-certificates.crt ]; then \
	  cp /etc/ssl/certs/ca-certificates.crt docker/ca-bundle.crt; \
	else \
	  : > docker/ca-bundle.crt; \
	fi

setup: ## Install api + web dev deps
	cd $(API_DIR) && uv sync --all-extras
	cd $(WEB_DIR) && npm install

lint: ## Lint api + web
	cd $(API_DIR) && uv run ruff check app tests
	cd $(WEB_DIR) && npm run lint

typecheck: ## mypy --strict + tsc --noEmit
	cd $(API_DIR) && uv run mypy app
	cd $(WEB_DIR) && npm run typecheck

test: ## Run pytest + vitest
	cd $(API_DIR) && uv run pytest -q
	cd $(WEB_DIR) && npm test -- --run

build: prebuild ## Build docker images
	$(COMPOSE) build

up: prebuild ## Bring the stack up (http://localhost:8080)
	$(COMPOSE) up -d --build
	@echo "==> waiting for services to become healthy..."
	@bash scripts/wait-healthy.sh || ($(COMPOSE) ps; $(COMPOSE) logs --tail=120; exit 1)
	@echo "==> stack up at http://localhost:8080"

down: ## Tear down the stack and prune volumes
	$(COMPOSE) down -v --remove-orphans

logs: ## Tail compose logs
	$(COMPOSE) logs -f --tail=200

migrate: ## Run alembic migrations inside the api container
	$(COMPOSE) exec -T api alembic upgrade head

smoke: ## Curl health + SSE + ingest a sample reading
	@bash scripts/smoke.sh

check: lint typecheck test build ## Everything CI would run (no runtime)

verify: check up migrate smoke ## Full local end-to-end gate
	@$(MAKE) down
	@echo "==> verify OK"

clean: ## Remove build artifacts (keeps node_modules / .venv)
	rm -rf $(WEB_DIR)/dist $(API_DIR)/.pytest_cache $(API_DIR)/.mypy_cache $(API_DIR)/.ruff_cache
