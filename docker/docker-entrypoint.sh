#!/bin/sh
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -eu

DATA_DIR="${DATA_DIR:-/data}"
APP_PORT="${APP_PORT:-8765}"
FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"
APP_SECRET_KEY_FILE="${APP_SECRET_KEY_FILE:-$DATA_DIR/.app-secret-key}"
INITIAL_ADMIN_PASSWORD_FILE="${INITIAL_ADMIN_PASSWORD_FILE:-$DATA_DIR/.initial-admin-password}"
DB_FILE="$DATA_DIR/caltopo-history.db"

mkdir -p "$DATA_DIR"
chown -R caltopo:caltopo "$DATA_DIR"
umask 077

is_missing_secret() {
  case "${1:-}" in
    ""|change-me|change-me-to-a-long-random-string|CHANGE_ME_LONG_RANDOM_SECRET|CHANGE_ME_LONG_RANDOM_PASSWORD) return 0 ;;
    *) return 1 ;;
  esac
}

# APP_SECRET_KEY is a persistent installation secret. Explicit environment input
# remains supported, otherwise Docker generates it once and stores it in /data.
if is_missing_secret "${APP_SECRET_KEY:-}"; then
  if [ ! -s "$APP_SECRET_KEY_FILE" ]; then
    if [ -s "$DB_FILE" ]; then
      echo >&2 "ERROR: Existing database found but APP_SECRET_KEY is not configured and $APP_SECRET_KEY_FILE is missing."
      echo >&2 "Restore the original APP_SECRET_KEY/secret file. Refusing to generate a replacement for an existing installation."
      exit 64
    fi
    python -c 'import secrets; print(secrets.token_hex(48))' > "$APP_SECRET_KEY_FILE"
    chown caltopo:caltopo "$APP_SECRET_KEY_FILE"
    chmod 0600 "$APP_SECRET_KEY_FILE"
    echo "Generated persistent APP_SECRET_KEY in $APP_SECRET_KEY_FILE."
  fi
  export APP_SECRET_KEY=""
  export APP_SECRET_KEY_FILE
fi

# On a fresh database, generate a strong temporary admin password if the operator
# did not provide one. The application deletes this plaintext file immediately
# after hashing the password into SQLite.
if [ ! -s "$DB_FILE" ]; then
  if is_missing_secret "${APP_PASSWORD:-}"; then
    if [ ! -s "$INITIAL_ADMIN_PASSWORD_FILE" ]; then
      python -c 'import secrets; print(secrets.token_urlsafe(24))' > "$INITIAL_ADMIN_PASSWORD_FILE"
      chown caltopo:caltopo "$INITIAL_ADMIN_PASSWORD_FILE"
      chmod 0600 "$INITIAL_ADMIN_PASSWORD_FILE"
    fi
    export APP_PASSWORD=""
    export INITIAL_ADMIN_PASSWORD_FILE
    echo ""
    echo "============================================================"
    echo "CalTopo History initial administrator credentials"
    echo "Username: ${APP_USERNAME:-admin}"
    printf 'Temporary password: '
    cat "$INITIAL_ADMIN_PASSWORD_FILE"
    echo "Change this password after the first login."
    echo "The temporary plaintext password file is removed after bootstrap."
    echo "============================================================"
    echo ""
  fi
else
  # Clean up a stale pending-password file from an interrupted older bootstrap.
  rm -f "$INITIAL_ADMIN_PASSWORD_FILE" 2>/dev/null || true
fi

umask 027
exec gosu caltopo:caltopo /usr/bin/tini -- python -m uvicorn app.main:app \
  --host 0.0.0.0 --port "$APP_PORT" --workers 1 --proxy-headers \
  --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
