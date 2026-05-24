#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"

. "$ROOT_DIR/frontend/scripts/ensure-pnpm.sh"

if [ "$#" -eq 0 ]; then
  exit 0
fi

files=()
for file in "$@"; do
  files+=("${file#frontend/}")
done

ensure_pnpm
cd "$ROOT_DIR/frontend"
pnpm exec prettier --write "${files[@]}"
