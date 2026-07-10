#!/bin/sh
set -e

# Producción: las migraciones se ejecutan en el servicio one-shot `migrate` de Compose.
# Este entrypoint solo arranca la API.
exec uvicorn main:app --host 0.0.0.0 --port 8000
