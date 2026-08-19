#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
NAME="caltopo-history.db.pre-docker-${STAMP}.bak"

CID="$(docker compose ps -q caltopo-history)"
if [[ -z "$CID" ]]; then
  echo "Container caltopo-history is not running." >&2
  exit 1
fi

docker compose exec -T --user 10001:10001 caltopo-history python - "$NAME" <<'PY'
import sqlite3, sys
from pathlib import Path
name = sys.argv[1]
src = Path('/data/caltopo-history.db')
dst = Path('/data') / name
if not src.exists():
    raise SystemExit('Database does not exist: /data/caltopo-history.db')
with sqlite3.connect(src) as source, sqlite3.connect(dst) as target:
    source.backup(target)
print(dst)
PY

docker cp "${CID}:/data/${NAME}" "./backups/${NAME}"
echo "Backup created in container volume and exported to: ./backups/${NAME}"
