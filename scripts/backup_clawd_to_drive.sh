#!/usr/bin/env bash
set -euo pipefail

# Backup /home/ubuntu/clawd to Google Drive folder "MoltoBot" as clawd.tar (overwrite-style).
# Uses gogcli (gog) auth + file keyring.

ACCOUNT="ryandeathridge@gmail.com"
FOLDER_ID="1-IGg2XG8_rNqhdF1L0pw2Rh_gwSMfu8d"   # MoltoBot
NAME="clawd.tar"
SRC_DIR="/home/ubuntu/clawd"
OUT="/home/ubuntu/clawd.tar"
GOG_BIN="/home/ubuntu/.local/bin/gog"
PASSFILE="$HOME/.config/gogcli/keyring_password"

export GOG_ACCOUNT="$ACCOUNT"
export GOG_KEYRING_BACKEND=file
export GOG_KEYRING_PASSWORD
GOG_KEYRING_PASSWORD="$(cat "$PASSFILE")"

# 1) Delete existing clawd.tar in folder (moves to trash)
# gog drive ls --plain output:
# ID\tNAME\tTYPE\tSIZE\tMODIFIED
existing_ids="$($GOG_BIN drive ls --parent "$FOLDER_ID" --query "name='$NAME'" --plain | awk 'NR>1 && $1!="" {print $1}')"
if [[ -n "$existing_ids" ]]; then
  while IFS= read -r fid; do
    [[ -z "$fid" ]] && continue
    $GOG_BIN drive delete "$fid" --force --no-input --plain >/dev/null
  done <<< "$existing_ids"
fi

# 2) Create tar (uncompressed)
# Include bot secret vault (low-risk credentials) so it is recoverable.
rm -f "$OUT"
# Archive from /home/ubuntu to keep paths stable.
# Includes:
# - clawd workspace
# - .clawdbot/secrets (age key + encrypted vault)
tar -cf "$OUT" -C "/home/ubuntu" "$(basename "$SRC_DIR")" ".clawdbot/secrets"

# 3) Upload
$GOG_BIN drive upload "$OUT" --parent "$FOLDER_ID" --name "$NAME" --plain >/dev/null

echo "OK: uploaded $NAME to MoltoBot (folderId=$FOLDER_ID) at $(date -Is)"
