#!/usr/bin/env bash
set -euo pipefail

# Run alembic migrations (if alembic is available)
if command -v alembic >/dev/null 2>&1; then
  echo "Running alembic migrations..."
  alembic -c /app/alembic.ini upgrade head || true
else
  echo "alembic not installed, skipping migrations"
fi

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
