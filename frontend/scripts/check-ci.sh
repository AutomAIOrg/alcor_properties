#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"
MODE="${1:---all}"

ensure_pnpm() {
  if ! command -v pnpm >/dev/null 2>&1; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm use --silent
  fi

  if ! command -v pnpm >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1; then
    corepack enable
  fi

  command -v pnpm >/dev/null 2>&1 || {
    echo "pnpm is not installed. Install frontend dependencies before running frontend CI checks."
    exit 1
  }
}

run_quick_checks() {
  cd "$ROOT_DIR/frontend"

  pnpm lint
  pnpm exec prettier --check "src/**/*.{ts,html,scss}"
  pnpm typecheck
}

run_heavy_checks() {
  cd "$ROOT_DIR/frontend"

  pnpm test:ci
  pnpm build
}

ensure_pnpm

case "$MODE" in
  --quick)
    run_quick_checks
    ;;
  --heavy)
    run_heavy_checks
    ;;
  --all)
    run_quick_checks
    run_heavy_checks
    ;;
  *)
    echo "Usage: frontend/scripts/check-ci.sh [--quick|--heavy]"
    exit 1
    ;;
esac
