.PHONY: setup lint typecheck test test-api test-lambdas synth deploy destroy

SERVICES := services/api services/panel-processor services/knmi-poller

# ── Setup ────────────────────────────────────────────────────────────────────
setup:
	uv tool install pre-commit
	@for s in $(SERVICES); do \
		echo "==> uv sync $$s"; \
		cd $$s && uv sync && cd ../..; \
	done
	@if [ -f infra/package.json ]; then cd infra && npm install && cd ..; fi
	@if [ -f frontend/package.json ]; then cd frontend && npm install && cd ..; fi
	pre-commit install

# ── Lint ─────────────────────────────────────────────────────────────────────
lint:
	@for s in $(SERVICES); do \
		echo "==> lint $$s"; \
		cd $$s && uv run ruff check . && uv run black --check . && uv run isort --check . && cd ../..; \
	done

# ── Type check ───────────────────────────────────────────────────────────────
typecheck:
	@for s in $(SERVICES); do \
		echo "==> mypy $$s"; \
		cd $$s && uv run mypy --strict . && cd ../..; \
	done
	@if [ -f infra/package.json ]; then cd infra && npm run build && cd ..; fi

# ── Tests ────────────────────────────────────────────────────────────────────
test:
	@for s in $(SERVICES); do \
		echo "==> pytest $$s"; \
		cd $$s && uv run pytest && cd ../..; \
	done

test-api:
	cd services/api && uv run pytest -v

test-lambdas:
	cd services/panel-processor && uv run pytest -v
	cd services/knmi-poller && uv run pytest -v

# ── CDK ──────────────────────────────────────────────────────────────────────
synth:
	cd infra && npm run build && npx cdk synth

deploy:
	cd infra && npm run build && npx cdk deploy --all

destroy:
	cd infra && npx cdk destroy --all
