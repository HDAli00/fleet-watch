#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/home/user/solarwatch}"
cd "$PROJECT_DIR"

echo "==> Fleet Telemetry — session start hook"

if ! command -v uv &>/dev/null; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
export PATH="$HOME/.local/bin:$PATH"

if ! command -v node &>/dev/null; then
  echo "==> Installing Node.js LTS..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
fi

if [ -f "$PROJECT_DIR/app/api/pyproject.toml" ]; then
  echo "==> Syncing app/api..."
  cd "$PROJECT_DIR/app/api" && uv sync && cd "$PROJECT_DIR"
fi

if [ -f "$PROJECT_DIR/app/web/package.json" ]; then
  echo "==> Installing app/web deps..."
  cd "$PROJECT_DIR/app/web" && npm install && cd "$PROJECT_DIR"
fi

echo "==> Session start complete"
