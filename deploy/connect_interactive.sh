#!/usr/bin/env bash
# Interactive helper: prompt for missing connector env vars, update .env, restart brain, verify.
# Never prints secret values.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$HERE/.." && pwd)"
TARGET="${BRAIN_DIR}/.env"
EXAMPLE="${BRAIN_DIR}/.env.example"
BRAIN_URL="${BRAIN_URL:-http://127.0.0.1:8000}"

[ -f "$EXAMPLE" ] || { echo "Missing $EXAMPLE"; exit 1; }
[ -f "$TARGET" ] || cp "$EXAMPLE" "$TARGET"

get_var() {
  local key="$1"
  grep -m1 "^${key}=" "$TARGET" 2>/dev/null | cut -d= -f2- || true
}

is_set() {
  local key="$1"
  local val
  val="$(get_var "$key")"
  [ -n "${val// }" ]
}

set_var() {
  local key="$1" val="$2"
  [ -z "$val" ] && return 0
  if grep -q "^${key}=" "$TARGET"; then
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

prompt_secret() {
  local key="$1" hint="$2"
  local val=""
  echo ""
  echo "── $key ──"
  echo "   $hint"
  read -r -s -p "   Paste value (Enter to skip): " val
  echo ""
  if [ -n "$val" ]; then
    set_var "$key" "$val"
    echo "   ✓ saved $key"
  else
    echo "   · skipped"
  fi
}

prompt_plain() {
  local key="$1" hint="$2" default="${3:-}"
  local val=""
  echo ""
  echo "── $key ──"
  echo "   $hint"
  if [ -n "$default" ]; then
    read -r -p "   Value [${default}]: " val
    val="${val:-$default}"
  else
    read -r -p "   Value: " val
  fi
  if [ -n "$val" ]; then
    set_var "$key" "$val"
    echo "   ✓ saved $key"
  else
    echo "   · skipped"
  fi
}

echo "==> Goldfront OS — interactive connector setup"
echo "    .env: $TARGET"
echo "    (secrets are never echoed)"
echo ""

# Defaults for non-secret vars
is_set GOLDFRONT_OWNER || set_var GOLDFRONT_OWNER lindsey
is_set CLICKUP_AUTO_SYNC || set_var CLICKUP_AUTO_SYNC true
is_set CLICKUP_WORKSPACE_ID || set_var CLICKUP_WORKSPACE_ID 90141259054
is_set GOOGLE_CALENDAR_ID || set_var GOOGLE_CALENDAR_ID primary
is_set FIELDY_API_BASE || set_var FIELDY_API_BASE https://api.fieldy.ai
is_set FIELDY_SPEAKER_ME || set_var FIELDY_SPEAKER_ME Lindsey

# Anthropic (not in /connectors/status but needed for /chat)
is_set ANTHROPIC_API_KEY || prompt_secret ANTHROPIC_API_KEY \
  "https://console.anthropic.com/settings/keys → Create Key"

# ClickUp
is_set CLICKUP_API_TOKEN || prompt_secret CLICKUP_API_TOKEN \
  "https://app.clickup.com/settings/apps → API Token"
is_set CLICKUP_WORKSPACE_ID || prompt_plain CLICKUP_WORKSPACE_ID \
  "ClickUp workspace ID" "90141259054"

# Fieldy
is_set FIELDY_API_TOKEN || prompt_secret FIELDY_API_TOKEN \
  "https://fieldy.ai → account / API settings"

# Google OAuth trio
if ! is_set GOOGLE_CLIENT_ID || ! is_set GOOGLE_CLIENT_SECRET || ! is_set GOOGLE_REFRESH_TOKEN; then
  echo ""
  echo "── Google (Calendar + Gmail) ──"
  echo "   1) Create OAuth Desktop client: https://console.cloud.google.com/apis/credentials"
  echo "   2) Enable Calendar API + Gmail API on the project"
  echo "   3) Run: python3 scripts/google_oauth_setup.py  (after CLIENT_ID + SECRET are set)"
  echo ""
  is_set GOOGLE_CLIENT_ID || prompt_secret GOOGLE_CLIENT_ID \
    "OAuth 2.0 Client ID"
  is_set GOOGLE_CLIENT_SECRET || prompt_secret GOOGLE_CLIENT_SECRET \
    "OAuth 2.0 Client Secret"
  if is_set GOOGLE_CLIENT_ID && is_set GOOGLE_CLIENT_SECRET && ! is_set GOOGLE_REFRESH_TOKEN; then
    echo ""
    read -r -p "   Run google_oauth_setup.py now? [y/N]: " run_oauth
    if [[ "${run_oauth,,}" == "y" ]]; then
      (cd "$BRAIN_DIR" && python3 scripts/google_oauth_setup.py) || true
    else
      is_set GOOGLE_REFRESH_TOKEN || prompt_secret GOOGLE_REFRESH_TOKEN \
        "Refresh token (from OAuth flow or OAuth Playground)"
    fi
  fi
fi

# Whoop
is_set WHOOP_ACCESS_TOKEN || prompt_secret WHOOP_ACCESS_TOKEN \
  "https://developer.whoop.com → register app → OAuth access token"

# Apple Health (optional on Mac)
if ! is_set APPLE_HEALTH_EXPORT_PATH; then
  echo ""
  echo "── APPLE_HEALTH_EXPORT_PATH (optional) ──"
  echo "   N/A unless you have a local JSON health export. Press Enter to skip."
  prompt_plain APPLE_HEALTH_EXPORT_PATH "Absolute path to health JSON export" ""
fi

echo ""
echo "==> Restarting brain (uvicorn on :8000)…"
UVICORN_PIDS="$(pgrep -f 'uvicorn brain.main:app' 2>/dev/null || true)"
if [ -n "$UVICORN_PIDS" ]; then
  echo "$UVICORN_PIDS" | xargs kill 2>/dev/null || true
  sleep 1
fi

if [ -d "${BRAIN_DIR}/.venv" ]; then
  # shellcheck disable=SC1091
  (
    cd "$BRAIN_DIR"
    source .venv/bin/activate
    export GOLDFRONT_OWNER="${GOLDFRONT_OWNER:-lindsey}"
    nohup uvicorn brain.main:app --host 0.0.0.0 --port 8000 > /tmp/goldfront-brain.log 2>&1 &
  )
  sleep 2
  echo "   ✓ uvicorn restarted (log: /tmp/goldfront-brain.log)"
else
  echo "   !! No .venv — restart manually:"
  echo "      cd $BRAIN_DIR && source .venv/bin/activate && uvicorn brain.main:app --host 0.0.0.0 --port 8000"
fi

echo ""
echo "==> Connector status:"
if command -v python3 >/dev/null; then
  curl -sf "${BRAIN_URL}/connectors/status" | python3 -m json.tool
else
  curl -sf "${BRAIN_URL}/connectors/status"
fi
echo ""

echo "==> SET / UNSET summary (no values):"
for key in ANTHROPIC_API_KEY CLICKUP_API_TOKEN CLICKUP_WORKSPACE_ID \
  GHL_API_KEY GHL_LOCATION_ID FIELDY_API_TOKEN \
  GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REFRESH_TOKEN \
  WHOOP_ACCESS_TOKEN APPLE_HEALTH_EXPORT_PATH; do
  if is_set "$key"; then echo "  $key=SET"; else echo "  $key=UNSET"; fi
done

echo ""
echo "Open Connections UI: ${BRAIN_URL}/#connections"
