#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database to accept connections..."
wait_retries=60
wait_delay=2
count=1
while [ $count -le $wait_retries ]
do
  if python - <<'PY'
import os,sys
try:
    import psycopg2
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        sys.exit(2)
    conn = psycopg2.connect(dsn, connect_timeout=2)
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
  then
    echo "Database is reachable; running alembic upgrade head"
    alembic -c /app/alembic.ini upgrade head
    exit 0
  else
    echo "DB not ready (attempt $count/$wait_retries), sleeping ${wait_delay}s"
    count=$((count+1))
    sleep $wait_delay
  fi
done

echo "Timed out waiting for DB; aborting migrations." >&2
exit 1
