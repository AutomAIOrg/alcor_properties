#!/usr/bin/env bash
set -eu

ROOT_DIR="$(git rev-parse --show-toplevel)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.test.yml"
BASELINE_SCHEMA="$ROOT_DIR/backend/tests/fixtures/baseline_schema.sql"
BASELINE_REVISION_FILE="$ROOT_DIR/backend/alembic/.baseline-revision"
COMPOSE_CMD=()
MODE="${1:---all}"

cleanup() {
  if [ "${#COMPOSE_CMD[@]}" -gt 0 ]; then
    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" down -v
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "$1 is not installed. Install the required CI dependency before running this script."
    exit 1
  }
}

read_baseline_revision() {
  [ -s "$BASELINE_REVISION_FILE" ] || {
    echo "Missing Alembic baseline revision: $BASELINE_REVISION_FILE"
    exit 1
  }

  local baseline_revision
  baseline_revision="$(tr -d '[:space:]' < "$BASELINE_REVISION_FILE")"

  [ -n "$baseline_revision" ] || {
    echo "Alembic baseline revision file is empty: $BASELINE_REVISION_FILE"
    exit 1
  }

  printf '%s' "$baseline_revision"
}

detect_compose() {
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
  elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
  else
    echo "Docker Compose is not installed. Install docker-compose or the Docker Compose plugin."
    exit 1
  fi
}

require_docker_daemon() {
  command -v docker >/dev/null 2>&1 || {
    echo "docker is not installed. Install Docker before running backend CI checks."
    exit 1
  }

  docker info >/dev/null 2>&1 || {
    echo "Docker is not available. Start Docker or check that your user can access the Docker daemon."
    exit 1
  }
}

require_free_port() {
  local host="$1"
  local port="$2"

  if command -v nc >/dev/null 2>&1; then
    if nc -z "$host" "$port" >/dev/null 2>&1; then
      echo "Port ${port} is already in use. Stop the process using it or change DB_PORT."
      exit 1
    fi
  elif command -v ss >/dev/null 2>&1; then
    if ss -ltn "sport = :$port" | tail -n +2 | grep -q .; then
      echo "Port ${port} is already in use. Stop the process using it or change DB_PORT."
      exit 1
    fi
  elif command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "Port ${port} is already in use. Stop the process using it or change DB_PORT."
      exit 1
    fi
  else
    echo "Neither nc, ss nor lsof is installed. Install one of them to check whether DB_PORT is free."
    exit 1
  fi
}

run_quick_checks() {
  require_command ruff

  python -m mypy --version >/dev/null 2>&1 || {
    echo "mypy is not installed. Install backend CI dependencies first."
    exit 1
  }

  cd "$ROOT_DIR/backend"

  ruff check .
  ruff format --check .

  python -m mypy \
    api/ application/ domain/ infrastructure/ config.py main.py \
    --config-file pyproject.toml \
    --explicit-package-bases
}

run_heavy_checks() {
  export DB_HOST=127.0.0.1
  export DB_USER=alcor
  export DB_PASS=alcor_pass
  export DB_NAME=alcor_test
  export DB_PORT=3307
  export ALCOR_IGNORE_ENV_FILE=1
  export DEBUG=false

  detect_compose
  require_docker_daemon
  require_command alembic

  [ -f "$BASELINE_SCHEMA" ] || {
    echo "Missing baseline schema fixture: $BASELINE_SCHEMA"
    exit 1
  }

  python -m pytest --version >/dev/null 2>&1 || {
    echo "pytest is not installed. Install backend test dependencies first."
    exit 1
  }

  trap cleanup EXIT INT TERM
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" down -v
  require_free_port "$DB_HOST" "$DB_PORT"
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d

  echo "Waiting for MySQL test database on ${DB_HOST}:${DB_PORT}..."
  attempts=0
  max_attempts=60

  while :; do
    if command -v mysqladmin >/dev/null 2>&1; then
      if mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" --silent; then
        break
      fi
    elif command -v nc >/dev/null 2>&1; then
      if nc -z "$DB_HOST" "$DB_PORT"; then
        break
      fi
    else
      echo "Neither mysqladmin nor nc is installed. Install one of them to wait for MySQL."
      exit 1
    fi

    attempts=$((attempts + 1))
    if [ "$attempts" -ge "$max_attempts" ]; then
      echo "MySQL test database did not become ready on ${DB_HOST}:${DB_PORT}."
      exit 1
    fi

    sleep 1
  done

  cd "$ROOT_DIR/backend"
  baseline_revision="$(read_baseline_revision)"

  python - <<'PY'
import os
from pathlib import Path

import pymysql

schema_path = Path("tests/fixtures/baseline_schema.sql")
connection = pymysql.connect(
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    database=os.environ["DB_NAME"],
    autocommit=True,
)

try:
    with connection.cursor() as cursor:
        for statement in schema_path.read_text().split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
finally:
    connection.close()
PY

  alembic stamp "$baseline_revision"
  alembic upgrade head
  python -m pytest tests/ --cov --cov-report=term-missing
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
    echo "Usage: backend/scripts/check-ci.sh [--quick|--heavy]"
    exit 1
    ;;
esac
