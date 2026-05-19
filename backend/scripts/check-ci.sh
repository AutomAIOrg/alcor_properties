#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

export DB_HOST=127.0.0.1
export DB_USER=alcor
export DB_PASS=alcor_pass
export DB_NAME=alcor_test
export DB_PORT=3306

command -v ruff >/dev/null 2>&1 || {
  echo "ruff is not installed. Install backend CI dependencies first."
  exit 1
}

ruff check .
ruff format --check .

python -m mypy \
  api/ application/ domain/ infrastructure/ config.py main.py \
  --config-file pyproject.toml \
  --explicit-package-bases

alembic upgrade head
python -m pytest tests/ --cov --cov-report=term-missing
