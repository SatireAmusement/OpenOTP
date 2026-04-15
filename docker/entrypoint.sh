#!/bin/sh
set -eu

echo "Waiting for database..."
until python -c "from sqlalchemy import create_engine, text; from app.core.config import get_settings; engine = create_engine(get_settings().database_url, pool_pre_ping=True); conn = engine.connect(); conn.execute(text('SELECT 1')); conn.close()"; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

exec "$@"
