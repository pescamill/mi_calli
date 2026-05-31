#!/usr/bin/env bash
set -euo pipefail

if [ $# -gt 0 ]; then
    exec "$@"
fi

# Start the app (for local testing we use SQLAlchemy's create_all)
echo "Starting application (Alembic handled by separate migrate service)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
