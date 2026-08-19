#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/caltopo-history.db" >&2
  exit 64
fi

SRC="$(realpath "$1")"
if [[ ! -f "$SRC" ]]; then
  echo "Database file not found: $SRC" >&2
  exit 66
fi

cd "$(dirname "$0")/.."

echo "Stopping application before database import..."
docker compose stop caltopo-history >/dev/null 2>&1 || true

# Create/initialize the service image and copy the supplied SQLite DB into the
# persistent /data volume as root, then hand ownership to the runtime user.
docker compose run --rm --no-deps \
  --entrypoint /bin/sh \
  -v "${SRC}:/import/source.db:ro" \
  caltopo-history \
  -c 'cp /import/source.db /data/caltopo-history.db && chown 10001:10001 /data/caltopo-history.db && chmod 0640 /data/caltopo-history.db'

echo "Starting application..."
docker compose up -d caltopo-history

echo "Imported: $SRC"
echo "Check with: docker compose logs --tail=100 caltopo-history"
