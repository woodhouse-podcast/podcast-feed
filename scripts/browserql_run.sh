#!/usr/bin/env bash
set -euo pipefail

# Simple single-flight wrapper for BrowserQL scripts.
# Ensures we don't exceed Browserless concurrency limits.

LOCKDIR="/tmp/browserql.lock"
WAIT_SECS=180

start_ts=$(date +%s)

while ! mkdir "$LOCKDIR" 2>/dev/null; do
  now=$(date +%s)
  if (( now - start_ts > WAIT_SECS )); then
    echo "BrowserQL busy (lock held > ${WAIT_SECS}s): $LOCKDIR" >&2
    exit 75
  fi
  sleep 1
done

cleanup() {
  rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

echo "BrowserQL lock acquired"
exec "$@"
