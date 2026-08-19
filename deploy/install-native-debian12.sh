#!/bin/sh
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -eu

if [ "$(id -u)" -ne 0 ]; then echo "Run this installer as root." >&2; exit 1; fi
SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR=/opt/caltopo-history
DATA_DIR=/var/lib/caltopo-history
ENV_FILE=/etc/caltopo-history.env
SERVICE_USER=caltopo-history

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip ca-certificates curl iproute2
if ! getent passwd "$SERVICE_USER" >/dev/null 2>&1; then useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"; fi
install -d -o root -g root -m 0755 "$APP_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0700 "$DATA_DIR"
rm -rf "$APP_DIR/app" "$APP_DIR/tests" "$APP_DIR/deploy"
cp -a "$SRC_DIR/app" "$APP_DIR/"
cp -a "$SRC_DIR/tests" "$APP_DIR/"
cp -a "$SRC_DIR/deploy" "$APP_DIR/"
install -m 0644 "$SRC_DIR/requirements.txt" "$APP_DIR/requirements.txt"
install -m 0644 "$SRC_DIR/pytest.ini" "$APP_DIR/pytest.ini"
install -m 0644 "$SRC_DIR/LICENSE" "$APP_DIR/LICENSE"
install -m 0644 "$SRC_DIR/THIRD-PARTY-NOTICES.md" "$APP_DIR/THIRD-PARTY-NOTICES.md"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
if [ ! -f "$ENV_FILE" ]; then
  install -o root -g root -m 0600 "$SRC_DIR/deploy/caltopo-history.env.example" "$ENV_FILE"
  echo "Created $ENV_FILE. Edit the CHANGE_ME values before starting the service."
else echo "Keeping existing $ENV_FILE unchanged."; fi
install -o root -g root -m 0644 "$SRC_DIR/deploy/caltopo-history.service" /etc/systemd/system/caltopo-history.service
systemctl daemon-reload
systemctl enable caltopo-history.service
if ss -ltn 2>/dev/null | grep -q "127.0.0.1:8765"; then echo "WARNING: TCP port 8765 is already in use." >&2; fi
echo "Installation complete. Edit $ENV_FILE, start the service, test /healthz and configure your HTTPS reverse proxy."
