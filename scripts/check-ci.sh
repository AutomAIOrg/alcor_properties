#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"
MODE="${1:---all}"

export LANG=C.utf8
export LC_ALL=C.utf8

. "$ROOT_DIR/frontend/scripts/ensure-pnpm.sh"
ensure_pnpm

if [ -d "$ROOT_DIR/backend/.venv" ]; then
  . "$ROOT_DIR/backend/.venv/bin/activate"
elif [ -d "$ROOT_DIR/.venv" ]; then
  . "$ROOT_DIR/.venv/bin/activate"
else
  echo "Missing Python virtualenv. Create one and install backend CI dependencies before running CI checks."
  echo "Expected: python3.13 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt ruff==0.15.13 mypy==2.1.0"
  exit 1
fi

run_quick_checks() {
  "$ROOT_DIR/backend/scripts/check-ci.sh" --quick
  "$ROOT_DIR/frontend/scripts/check-ci.sh" --quick
}

run_heavy_checks() {
  "$ROOT_DIR/backend/scripts/check-ci.sh" --heavy
  "$ROOT_DIR/frontend/scripts/check-ci.sh" --heavy
}

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
    echo "Usage: scripts/check-ci.sh [--quick|--heavy|--all]"
    exit 1
    ;;
esac
