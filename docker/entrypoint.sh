#!/bin/bash
set -euo pipefail

echo "🔁 Container starting, initiating warm-up …"
if ! python /app/docker/prewarm.py; then
  echo "⚠️  Warm-up encountered issues. Continuing startup to avoid downtime."
fi

echo "🚀 Launching main process: $*"
exec "$@"
