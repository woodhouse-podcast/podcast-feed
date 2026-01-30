#!/usr/bin/env bash
set -euo pipefail

SECRETS_DIR="/home/ubuntu/.clawdbot/secrets"
KEY_FILE="$SECRETS_DIR/age.key"
VAULT_FILE="$SECRETS_DIR/vault.json.enc"

require_files() {
  [[ -f "$KEY_FILE" ]] || { echo "Missing $KEY_FILE" >&2; exit 2; }
  [[ -f "$VAULT_FILE" ]] || { echo "Missing $VAULT_FILE" >&2; exit 2; }
}

decrypt() {
  require_files
  age -d -i "$KEY_FILE" "$VAULT_FILE"
}

encrypt_from_stdin() {
  require_files
  local tmp
  tmp=$(mktemp)
  cat > "$tmp"
  # validate JSON before encrypting
  jq -e . "$tmp" >/dev/null
  local pub
  pub=$(age-keygen -y "$KEY_FILE")
  age -R <(echo "$pub") -o "$VAULT_FILE" "$tmp"
  rm -f "$tmp"
}

cmd_list() {
  decrypt | jq -r 'keys[]' | sort
}

cmd_get() {
  local key=${1:?"usage: vault.sh get <site>"}
  decrypt | jq -er --arg k "$key" '.[$k] // empty'
}

cmd_set() {
  local key=${1:?"usage: vault.sh set <site> <username> <password> [notes]"}
  local username=${2:?"usage: vault.sh set <site> <username> <password> [notes]"}
  local password=${3:?"usage: vault.sh set <site> <username> <password> [notes]"}
  local notes=${4:-""}

  decrypt | jq --arg k "$key" --arg u "$username" --arg p "$password" --arg n "$notes" \
    '.[$k] = {username:$u, password:$p, notes:$n, updatedAt:(now|todateiso8601)}' \
    | encrypt_from_stdin

  echo "OK" >&2
}

cmd_del() {
  local key=${1:?"usage: vault.sh del <site>"}
  decrypt | jq --arg k "$key" 'del(.[$k])' | encrypt_from_stdin
  echo "OK" >&2
}

cmd_export_json() {
  decrypt | jq '.'
}

cmd_help() {
  cat <<'EOF'
Usage:
  vault.sh list
  vault.sh get <site>
  vault.sh set <site> <username> <password> [notes]
  vault.sh del <site>
  vault.sh export-json

Notes:
- This is an on-box "low risk" vault. The encryption key lives on the same host.
- Avoid printing secrets into chat. Use this locally to fetch + fill forms.
EOF
}

main() {
  local cmd=${1:-help}
  shift || true
  case "$cmd" in
    list) cmd_list "$@";;
    get) cmd_get "$@";;
    set) cmd_set "$@";;
    del) cmd_del "$@";;
    export-json) cmd_export_json "$@";;
    help|--help|-h) cmd_help;;
    *) echo "Unknown command: $cmd" >&2; cmd_help; exit 2;;
  esac
}

main "$@"
