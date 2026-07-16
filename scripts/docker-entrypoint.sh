#!/bin/sh
set -eu

DB_PATH="${GUIDE_DB_PATH:-/app/runtime/guide.sqlite3}"
UPLOAD_PATH="${GUIDE_UPLOAD_DIR:-/app/runtime/uploads}"

mkdir -p "$(dirname "$DB_PATH")" "$UPLOAD_PATH"

if [ ! -f "$DB_PATH" ] && [ -f /app/data/guide.sqlite3 ]; then
    cp /app/data/guide.sqlite3 "$DB_PATH"
fi

if [ -d /app/server/app/static/admin/uploads ]; then
    cp -n /app/server/app/static/admin/uploads/* "$UPLOAD_PATH"/ 2>/dev/null || true
fi

exec uvicorn server.app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
