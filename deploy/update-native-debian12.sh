#!/bin/sh
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -eu

if [ "$(id -u)" -ne 0 ]; then echo "Run this updater as root." >&2; exit 1; fi
SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR=/opt/caltopo-history
DATA_DIR=/var/lib/caltopo-history
DB_FILE=$DATA_DIR/caltopo-history.db
ENV_FILE=/etc/caltopo-history.env
STAMP=$(date +%Y%m%d-%H%M%S)
if [ ! -d "$APP_DIR" ] || [ ! -f "$ENV_FILE" ]; then echo "Existing native installation not found. Use install-native-debian12.sh instead." >&2; exit 1; fi

if [ -f "$DB_FILE" ]; then
  DB_BYTES=$(wc -c < "$DB_FILE" | tr -d ' ')
  FREE_KB=$(df -Pk "$DATA_DIR" | awk 'NR==2 {print $4}')
  FREE_BYTES=$((FREE_KB * 1024))
  HARD_MB=$(python3 - "$DB_FILE" <<'PYDB'
import sqlite3, sys
try:
    con = sqlite3.connect(sys.argv[1])
    row = con.execute("SELECT value FROM app_settings WHERE key='disk_hard_free_mb'").fetchone()
    print(int(row[0]) if row else 2048)
except Exception:
    print(2048)
PYDB
)
  UPDATE_RESERVE_BYTES=$((HARD_MB * 1024 * 1024))
  REQUIRED_BYTES=$((DB_BYTES + UPDATE_RESERVE_BYTES))
  if [ "$FREE_BYTES" -lt "$REQUIRED_BYTES" ]; then
    echo "Update aborted: not enough free disk space for the mandatory database backup while preserving the hard free-space reserve." >&2
    exit 1
  fi
fi

systemctl stop caltopo-history.service || true
if [ -f "$DB_FILE" ]; then
  cp -a "$DB_FILE" "$DB_FILE.pre-v0.9-$STAMP.bak"
  chown caltopo-history:caltopo-history "$DB_FILE.pre-v0.9-$STAMP.bak"
  chmod 0600 "$DB_FILE.pre-v0.9-$STAMP.bak"
  echo "Database backup: $DB_FILE.pre-v0.9-$STAMP.bak"
fi
rm -rf "$APP_DIR/app" "$APP_DIR/tests" "$APP_DIR/deploy"
cp -a "$SRC_DIR/app" "$APP_DIR/"
cp -a "$SRC_DIR/tests" "$APP_DIR/"
cp -a "$SRC_DIR/deploy" "$APP_DIR/"
install -m 0644 "$SRC_DIR/requirements.txt" "$APP_DIR/requirements.txt"
install -m 0644 "$SRC_DIR/pytest.ini" "$APP_DIR/pytest.ini"
install -m 0644 "$SRC_DIR/LICENSE" "$APP_DIR/LICENSE"
install -m 0644 "$SRC_DIR/THIRD-PARTY-NOTICES.md" "$APP_DIR/THIRD-PARTY-NOTICES.md"
if [ ! -x "$APP_DIR/.venv/bin/pip" ]; then python3 -m venv "$APP_DIR/.venv"; fi
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
install -o root -g root -m 0644 "$SRC_DIR/deploy/caltopo-history.service" /etc/systemd/system/caltopo-history.service
systemctl daemon-reload
systemctl start caltopo-history.service
sleep 2
systemctl --no-pager --full status caltopo-history.service || true
curl --fail --silent --show-error http://127.0.0.1:8765/healthz
echo
echo "Update to CalTopo History v0.9 complete. Existing /etc/caltopo-history.env was not changed."
