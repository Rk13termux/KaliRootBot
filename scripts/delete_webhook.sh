#!/usr/bin/env bash
set -euo pipefail

# Helper to delete Telegram webhook using ENV vars.
# Usage: source .env && ./scripts/delete_webhook.sh

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "TELEGRAM_BOT_TOKEN not set"
  exit 1
fi

TOKEN=${TELEGRAM_BOT_TOKEN}

echo "Deleting webhook for token"
curl -s "https://api.telegram.org/bot${TOKEN}/deleteWebhook" | jq
