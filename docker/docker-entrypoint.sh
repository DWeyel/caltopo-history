#!/bin/sh
set -eu
DATA_DIR="${DATA_DIR:-/data}"
APP_PORT="${APP_PORT:-8765}"
FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"
mkdir -p "$DATA_DIR"
chown -R caltopo:caltopo "$DATA_DIR"
if [ "${APP_SECRET_KEY:-}" = "" ] || [ "${APP_SECRET_KEY:-}" = "change-me-to-a-long-random-string" ]; then echo >&2 "ERROR: APP_SECRET_KEY must be set to a long random value."; exit 64; fi
DB_FILE="$DATA_DIR/caltopo-history.db"
if [ ! -s "$DB_FILE" ]; then
  if [ "${APP_PASSWORD:-}" = "" ] || [ "${APP_PASSWORD:-}" = "change-me" ] || [ "${APP_PASSWORD:-}" = "CHANGE_ME_LONG_RANDOM_PASSWORD" ]; then echo >&2 "ERROR: APP_PASSWORD must be set for the initial admin account on a fresh database."; exit 64; fi
fi
umask 027
exec gosu caltopo:caltopo /usr/bin/tini -- python -m uvicorn app.main:app --host 0.0.0.0 --port "$APP_PORT" --workers 1 --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
