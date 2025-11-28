#!/usr/bin/env bash
set -euo pipefail

# Helper to set Telegram webhook using ENV vars.
# Usage: source .env && ./scripts/set_webhook.sh

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "TELEGRAM_BOT_TOKEN not set"
  exit 1
fi
if [ -z "${TELEGRAM_WEBHOOK_URL:-}" ]; then
  echo "TELEGRAM_WEBHOOK_URL not set"
  exit 1
fi

TOKEN=${TELEGRAM_BOT_TOKEN}
URL=${TELEGRAM_WEBHOOK_URL}
SECRET=${TELEGRAM_WEBHOOK_SECRET:-}

if [ -n "$SECRET" ]; then
  echo "Setting webhook: $URL with secret"
  curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook?url=${URL}&secret_token=${SECRET}" | jq
else
  echo "Setting webhook: $URL (no secret provided)"
  curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook?url=${URL}" | jq
fi
