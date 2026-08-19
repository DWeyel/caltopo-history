#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"
for archive in support/ui-assets-v0.8.tar.gz support/tests-v0.8.tar.gz support/deployment-tools-v0.8.tar.gz; do
  [ -f "$archive" ] || { echo >&2 "Missing $archive"; exit 1; }
  tar -xzf "$archive"
done
echo "Support files extracted into app/templates, app/static, tests, deploy and docker."
