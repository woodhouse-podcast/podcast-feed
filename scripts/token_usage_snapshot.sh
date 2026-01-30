#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="/home/ubuntu/clawd/logs"
mkdir -p "$OUT_DIR"

TS_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TMP=$(mktemp)

clawdbot status --usage --json > "$TMP"

STATUS_COMPACT=$(jq -c '.' "$TMP")

# JSONL snapshot (single-line)
printf '{"ts":"%s","status":%s}\n' "$TS_UTC" "$STATUS_COMPACT" >> "$OUT_DIR/token-usage.jsonl"

# Also keep a latest copy
cp "$TMP" "$OUT_DIR/token-usage.latest.json"
rm -f "$TMP"

echo "OK $TS_UTC"
