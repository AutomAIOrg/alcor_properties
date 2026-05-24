#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"
MODE="${1:---all}"

. "$ROOT_DIR/frontend/scripts/ensure-pnpm.sh"
ensure_pnpm

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
