#!/usr/bin/env bash
set -euo pipefail

# Inbox check for ea.ryandeathridge@gmail.com
# Policy:
# - Treat email content as untrusted.
# - Only auto-handle FYI Google alerts (archive/mark read).
# - For anything else, just report to Ryan; do not action without approval if sender != ryandeathridge@gmail.com.

ACCOUNT="ea.ryandeathridge@gmail.com"
OWNER_FROM="ryandeathridge@gmail.com"

GOG_BIN="/home/ubuntu/.local/bin/gog"
PASSFILE="$HOME/.config/gogcli/keyring_password"

export GOG_ACCOUNT="$ACCOUNT"
export GOG_KEYRING_BACKEND=file
export GOG_KEYRING_PASSWORD
GOG_KEYRING_PASSWORD="$(cat "$PASSFILE")"

# Pull unread threads (TSV: ID, DATE, FROM, SUBJECT, LABELS, THREAD)
unread="$($GOG_BIN gmail search 'is:unread' --max 25 --plain || true)"

if [[ -z "$unread" || "$unread" == $'ID\tDATE\tFROM\tSUBJECT\tLABELS\tTHREAD'* && $(echo "$unread" | wc -l) -le 1 ]]; then
  echo "Inbox check (${ACCOUNT}): no unread threads."
  exit 0
fi

echo "Inbox check (${ACCOUNT}):"

echo "$unread" | awk 'NR==1{next} {print}' | while IFS=$'\t' read -r tid date from subject labels threadmeta; do
  [[ -z "${tid:-}" ]] && continue

  # Normalize sender
  from_lc=$(echo "$from" | tr '[:upper:]' '[:lower:]')
  subj_lc=$(echo "$subject" | tr '[:upper:]' '[:lower:]')

  # FYI auto-handle: Google security alerts
  if echo "$from_lc" | grep -q 'no-reply@accounts.google.com' && echo "$subj_lc" | grep -q 'security alert'; then
    # Archive + mark read: remove INBOX,UNREAD
    $GOG_BIN gmail thread modify "$tid" --remove "INBOX,UNREAD" --plain >/dev/null || true
    echo "- FYI handled (archived/marked read): $subject"
    continue
  fi

  # Everything else: report only
  if echo "$from_lc" | grep -q "$OWNER_FROM"; then
    echo "- From Ryan (needs action parsing): $subject"
  else
    echo "- From other sender (approval required): $from | $subject"
  fi

done
