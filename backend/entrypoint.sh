#!/usr/bin/env bash
set -euo pipefail

# Start the app (for local testing we use SQLAlchemy's create_all)
echo "Starting application (skipping Alembic migrations)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
