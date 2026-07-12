#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "Usage: scripts/install_in_bench.sh /path/to/frappe-bench site.name" >&2
  exit 2
fi
BENCH_PATH="$1"
SITE_NAME="$2"
APP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BENCH_PATH"
bench get-app "$APP_PATH"
bench --site "$SITE_NAME" install-app factorypulse_erp
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" run-tests --app factorypulse_erp
