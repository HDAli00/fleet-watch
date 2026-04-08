#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/home/user/solarwatch}"
cd "$PROJECT_DIR"

echo "==> Solar IoT Platform — session start hook"

# ── uv (Python package manager) ────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

# Ensure uv is on PATH for the rest of this script
export PATH="$HOME/.local/bin:$PATH"

# ── Node / npm ──────────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "==> Installing Node.js LTS..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
fi

# ── pre-commit ──────────────────────────────────────────────────────────────
if ! command -v pre-commit &>/dev/null; then
  echo "==> Installing pre-commit..."
  uv tool install pre-commit
fi

# ── CDK infrastructure deps ─────────────────────────────────────────────────
if [ -f "infra/package.json" ]; then
  echo "==> Installing infra (CDK) deps..."
  cd "$PROJECT_DIR/infra" && npm install && cd "$PROJECT_DIR"
fi

# ── Python services: uv sync each (only if pyproject.toml exists) ──────────
for service in services/api services/panel-processor services/knmi-poller; do
  if [ -f "$PROJECT_DIR/$service/pyproject.toml" ]; then
    echo "==> Syncing $service..."
    cd "$PROJECT_DIR/$service" && uv sync && cd "$PROJECT_DIR"
  fi
done

# ── Frontend deps ────────────────────────────────────────────────────────────
if [ -f "frontend/package.json" ]; then
  echo "==> Installing frontend deps..."
  cd "$PROJECT_DIR/frontend" && npm install && cd "$PROJECT_DIR"
fi

echo "==> Session start complete"
