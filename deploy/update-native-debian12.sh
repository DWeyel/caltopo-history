#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this updater as root." >&2
    exit 1
fi

SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR=/opt/caltopo-history
DATA_DIR=/var/lib/caltopo-history
DB_FILE="$DATA_DIR/caltopo-history.db"
SERVICE_USER=caltopo-history

if [ ! -d "$APP_DIR" ] || [ ! -f /etc/systemd/system/caltopo-history.service ]; then
    echo "Existing native installation not found. Use install-native-debian12.sh for a fresh installation." >&2
    exit 1
fi

# Check free space before stopping the service or creating a safety copy.
# Reserve the configured hard free-space threshold after the copy.
HARD_MB=2048
if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(stat -c %s "$DB_FILE")
    FREE_BYTES=$(df -PB1 "$DATA_DIR" | awk 'NR==2 {print $4}')
    REQUIRED_BYTES=$((DB_SIZE + HARD_MB * 1024 * 1024))
    if [ "$FREE_BYTES" -lt "$REQUIRED_BYTES" ]; then
        echo "Not enough free space for the pre-update database backup plus the safety reserve." >&2
        exit 1
    fi
fi

systemctl stop caltopo-history.service

STAMP=$(date +%Y%m%d-%H%M%S)
if [ -f "$DB_FILE" ]; then
    cp -a "$DB_FILE" "$DB_FILE.pre-v0.10-$STAMP.bak"
    chown "$SERVICE_USER:$SERVICE_USER" "$DB_FILE.pre-v0.10-$STAMP.bak"
    chmod 0600 "$DB_FILE.pre-v0.10-$STAMP.bak"
    echo "Database backup: $DB_FILE.pre-v0.10-$STAMP.bak"
fi

rm -rf "$APP_DIR/app" "$APP_DIR/tests" "$APP_DIR/deploy"
cp -a "$SRC_DIR/app" "$APP_DIR/"
cp -a "$SRC_DIR/tests" "$APP_DIR/"
cp -a "$SRC_DIR/deploy" "$APP_DIR/"
install -m 0644 "$SRC_DIR/requirements.txt" "$APP_DIR/requirements.txt"
install -m 0644 "$SRC_DIR/pytest.ini" "$APP_DIR/pytest.ini"

if [ ! -x "$APP_DIR/.venv/bin/pip" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

chown -R root:root "$APP_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"

systemctl daemon-reload
systemctl start caltopo-history.service
sleep 2
curl --fail --silent --show-error http://127.0.0.1:8765/healthz
printf '\n'
echo "Update to CalTopo History v0.10 complete. Existing /etc/caltopo-history.env was not changed."
