#!/usr/bin/env bash
set -euo pipefail

# Search Gmail across ALL mailboxes (including Spam) for a query.
# Usage:
#   gmail_search_anywhere.sh 'from:github.com subject:(verification) newer_than:7d'

ACCOUNT="ea.ryandeathridge@gmail.com"
GOG_BIN="/home/ubuntu/.local/bin/gog"
PASSFILE="$HOME/.config/gogcli/keyring_password"

export GOG_ACCOUNT="$ACCOUNT"
export GOG_KEYRING_BACKEND=file
export GOG_KEYRING_PASSWORD
GOG_KEYRING_PASSWORD="$(cat "$PASSFILE")"

QUERY=${1:-}
if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 '<gmail search query>'" >&2
  exit 2
fi

# in:anywhere includes spam/trash.
$GOG_BIN gmail search "in:anywhere $QUERY" --max 25 --plain
