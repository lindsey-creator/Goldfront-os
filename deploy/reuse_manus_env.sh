#!/usr/bin/env bash
# Find connector credentials already on the Manus box (conradstrong.com / legacy theconradteam.com hosts)
# and merge into goldfront-os/.env. Never prints secret values.
# Fieldy: prefer copying FIELDY_API_TOKEN from your Mac .env; reuse_manus_env only fills gaps.
set -euo pipefail

BRAIN_DIR="${BRAIN_DIR:-$HOME/Documents/Claude/Projects/Brain/goldfront-os}"
TARGET="${BRAIN_DIR}/.env"
EXAMPLE="${BRAIN_DIR}/.env.example"

VARS=(
  GOLDFRONT_OWNER
  ANTHROPIC_API_KEY
  CLICKUP_API_TOKEN
  CLICKUP_WORKSPACE_ID
  CLICKUP_AUTO_SYNC
  GHL_API_KEY
  GHL_LOCATION_ID
  # FIELDY_API_TOKEN — copy from Mac goldfront-os/.env only (not auto-hunted here)
  FIELDY_API_BASE
  FIELDY_SPEAKER_ME
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  GOOGLE_CALENDAR_ID
  WHOOP_ACCESS_TOKEN
  APPLE_HEALTH_EXPORT_PATH
)

[ -f "$EXAMPLE" ] || { echo "Missing $EXAMPLE"; exit 1; }
[ -f "$TARGET" ] || cp "$EXAMPLE" "$TARGET"

get_var() {
  local file="$1" key="$2"
  grep -m1 "^${key}=" "$file" 2>/dev/null | cut -d= -f2- || true
}

set_var() {
  local key="$1" val="$2"
  [ -z "$val" ] && return 0
  if grep -q "^${key}=" "$TARGET"; then
    # portable in-place: rewrite line
    local tmp
    tmp="$(mktemp)"
    while IFS= read -r line; do
      if [[ "$line" == "${key}="* ]]; then
        echo "${key}=${val}"
      else
        echo "$line"
      fi
    done < "$TARGET" > "$tmp"
    mv "$tmp" "$TARGET"
  else
    echo "${key}=${val}" >> "$TARGET"
  fi
}

# Collect candidate env files (prioritize existing command center deployment)
PRIORITY=(
  "/var/www/dashboard/.env"
  "/var/www/dashboard/.env.local"
  "$HOME/Documents/Claude/Projects/Brain/goldfront-os/.env"
)
CANDIDATES=()
while IFS= read -r _line; do
  CANDIDATES+=("$_line")
done < <(
  printf '%s\n' "${PRIORITY[@]}"
  find "$HOME" /var/www /opt /srv /etc 2>/dev/null \
    \( -path '*/node_modules/*' -o -path '*/.venv/*' -o -path '*/.git/*' \) -prune \
    -o \( -name '.env' -o -name '.env.local' -o -name '.env.production' -o -name 'env' \) -print 2>/dev/null \
    | grep -v "^${TARGET}$"
)
# de-dupe while preserving order
declare -A SEEN=()
UNIQ=()
for f in "${CANDIDATES[@]}"; do
  [ -f "$f" ] || continue
  [ -n "${SEEN[$f]:-}" ] && continue
  SEEN[$f]=1
  UNIQ+=("$f")
done
CANDIDATES=("${UNIQ[@]:0:80}")

# Aliases from command.theconradteam.com dashboard → goldfront-os .env
apply_aliases() {
  local f="$1"
  [ -f "$f" ] || return 0
  local team personal loc
  team="$(get_var "$f" GHL_TEAM_PIT_TOKEN)"
  personal="$(get_var "$f" GHL_PERSONAL_PIT_TOKEN)"
  loc="$(get_var "$f" GHL_LOCATION_ID)"
  [ -z "$(get_var "$TARGET" GHL_API_KEY)" ] && [ -n "$team" ] && set_var GHL_API_KEY "$team" && echo "    + GHL_API_KEY (from GHL_TEAM_PIT_TOKEN) $(dirname "$f")/"
  [ -z "$(get_var "$TARGET" GHL_API_KEY)" ] && [ -n "$personal" ] && set_var GHL_API_KEY "$personal" && echo "    + GHL_API_KEY (from GHL_PERSONAL_PIT_TOKEN) $(dirname "$f")/"
  [ -z "$(get_var "$TARGET" GHL_LOCATION_ID)" ] && [ -n "$loc" ] && set_var GHL_LOCATION_ID "$loc" && echo "    + GHL_LOCATION_ID $(dirname "$f")/"
  [ -z "$(get_var "$TARGET" GHL_LOCATION_ID)" ] && [ -n "$team" ] && set_var GHL_LOCATION_ID FFdZCVGXSQQThtHZEOYx && echo "    + GHL_LOCATION_ID (team default)"
}

echo "==> Scanning ${#CANDIDATES[@]} env files for connector keys…"
FOUND=0
for f in "${CANDIDATES[@]}"; do
  apply_aliases "$f"
done
for key in "${VARS[@]}"; do
  cur="$(get_var "$TARGET" "$key")"
  [ -n "$cur" ] && continue
  for f in "${CANDIDATES[@]}"; do
    [ -f "$f" ] || continue
    val="$(get_var "$f" "$key")"
    if [ -n "$val" ]; then
      set_var "$key" "$val"
      echo "    + $key from $(dirname "$f")/"
      FOUND=$((FOUND + 1))
      break
    fi
  done
done

# Required defaults
[ -n "$(get_var "$TARGET" GOLDFRONT_OWNER)" ] || set_var GOLDFRONT_OWNER lindsey
[ -n "$(get_var "$TARGET" CLICKUP_AUTO_SYNC)" ] || set_var CLICKUP_AUTO_SYNC true
[ -n "$(get_var "$TARGET" CLICKUP_WORKSPACE_ID)" ] || set_var CLICKUP_WORKSPACE_ID 90141259054

echo "==> Merged $FOUND vars into $TARGET (values not shown)."
