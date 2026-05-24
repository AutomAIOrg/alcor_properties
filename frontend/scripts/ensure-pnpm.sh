#!/usr/bin/env bash

ensure_pnpm() {
  if ! command -v pnpm >/dev/null 2>&1; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

    if [ -s "$NVM_DIR/nvm.sh" ]; then
      . "$NVM_DIR/nvm.sh"
      command -v nvm >/dev/null 2>&1 && nvm use --silent
    fi
  fi

  if ! command -v pnpm >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1; then
    corepack enable
  fi

  command -v pnpm >/dev/null 2>&1 || {
    echo "pnpm is not installed. Install frontend dependencies before running frontend checks."
    exit 1
  }
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  set -eu
  ensure_pnpm
fi
