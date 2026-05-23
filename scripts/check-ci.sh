#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"

export LANG=C.utf8
export LC_ALL=C.utf8

if ! command -v pnpm >/dev/null 2>&1; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm use --silent
fi

if ! command -v pnpm >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1; then
  corepack enable
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is not installed. Install frontend dependencies before running CI checks."
  exit 1
fi

if [ -d "$ROOT_DIR/backend/.venv" ]; then
  . "$ROOT_DIR/backend/.venv/bin/activate"
elif [ -d "$ROOT_DIR/.venv" ]; then
  . "$ROOT_DIR/.venv/bin/activate"
else
  echo "Missing Python virtualenv. Create one and install backend CI dependencies before running CI checks."
  echo "Expected: python3.13 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt ruff==0.15.13 mypy==2.1.0"
  exit 1
fi

"$ROOT_DIR/backend/scripts/check-ci.sh" --quick
"$ROOT_DIR/frontend/scripts/check-ci.sh" --quick
"$ROOT_DIR/backend/scripts/check-ci.sh" --heavy
"$ROOT_DIR/frontend/scripts/check-ci.sh" --heavy
