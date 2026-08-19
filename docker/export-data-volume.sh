#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="backups/caltopo-history-data-${STAMP}.tar.gz"
VOLUME="${DATA_VOLUME_NAME:-caltopo_history_data}"

docker run --rm \
  -v "${VOLUME}:/data:ro" \
  -v "$(pwd)/backups:/backup" \
  alpine:3.20 \
  sh -c "tar -C /data -czf /backup/$(basename "$OUT") ."

echo "Volume export created: $OUT"
