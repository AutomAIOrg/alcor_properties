#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Aplicando migraciones pendientes..."
alembic upgrade head

echo "Arrancando servidor en modo desarrollo..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
