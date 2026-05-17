#!/bin/bash
set -e

echo "Aplicando migraciones pendientes..."
alembic upgrade head

echo "Arrancando servidor..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
