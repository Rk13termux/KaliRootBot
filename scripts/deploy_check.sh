#!/usr/bin/env bash
set -euo pipefail

# Usage: source .env && ./scripts/deploy_check.sh
# The script will validate the deployment health: /status, HEAD /, webhook info.

: "${TELEGRAM_BOT_TOKEN:?Please export TELEGRAM_BOT_TOKEN}")
: "${TELEGRAM_WEBHOOK_URL:?Please export TELEGRAM_WEBHOOK_URL}")

echo "==> Checking /status"
if curl -s --fail "${TELEGRAM_WEBHOOK_URL%/}"/status | jq . >/dev/null; then
  echo "OK: /status responds"
else
  echo "ERROR: /status did not respond or returned non-200"
  exit 1
fi

echo "==> Checking HEAD / (health check)"
if curl -s -I -X HEAD "${TELEGRAM_WEBHOOK_URL%/}" | head -n 1 | grep -E "200|204|301|302" >/dev/null; then
  echo "OK: HEAD / responsive"
else
  echo "WARN: HEAD / didn't return 200/204 (may be configured to use /status as health check)"
fi

if [ -n "${TELEGRAM_BOT_TOKEN}" ]; then
  echo "==> Checking Telegram webhook info"
  webhook=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo")
  echo "$webhook" | jq .
  url=$(echo "$webhook" | jq -r '.result.url // ""')
  if [ -z "$url" ]; then
    echo "WARN: Bot currently has no webhook set (getWebhookInfo url empty)"
  else
    echo "OK: webhook is set to: $url"
  fi
fi

echo "==> All checks passed (or reported warnings)."

exit 0
