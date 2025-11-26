#!/usr/bin/env bash
set -euo pipefail

# dev_test.sh: send test requests to a running local server
# Usage: ./dev_test.sh [--port PORT]

PORT=${1:-8000}
HOST=${HOST:-127.0.0.1}
URL_BASE="http://$HOST:$PORT"

# Test health endpoint
echo "Testing health endpoint: $URL_BASE/"
curl -sS -w "\nHTTP_CODE:%{http_code}\n" "$URL_BASE/"

# Prepare Telegram update payload
cat <<'JSON' > /tmp/telegram_update.json
{
  "update_id": 10000,
  "message": {
    "message_id": 1,
    "from": {"id": 12345, "is_bot": false, "first_name": "Dev"},
    "chat": {"id": 12345, "first_name": "Dev", "type": "private"},
    "date": 1609459200,
    "text": "Hola desde dev_test.sh"
  }
}
JSON

echo "Posting Telegram update to $URL_BASE/webhook/telegram"
curl -sS -H "Content-Type: application/json" -d @/tmp/telegram_update.json "$URL_BASE/webhook/telegram" || true

# Prepare Gumroad webhook payload and HMAC signature
BODY='{"event":"sale","product_permalink":"pack-100-creditos","custom_fields":{"telegram_user_id":"12345"}}'
GUM_SECRET=${GUMROAD_WEBHOOK_SECRET:-$(cat .env 2>/dev/null | sed -n 's/GUMROAD_WEBHOOK_SECRET=\?\"\?\([^\"\n]*\)\"\?/\1/p')}
if [ -z "$GUM_SECRET" ]; then
  echo "Gumroad secret not found; set GUMROAD_WEBHOOK_SECRET env var or include in .env to test the signature"
else
  printf -v SIG "$(python - <<PY
import hmac, hashlib, sys
s=b'%s'
body=b'%s'
print(hmac.new(s, body, hashlib.sha256).hexdigest())
PY
)" "$GUM_SECRET" "$BODY"
  echo "Posting Gumroad webhook (with signature) to $URL_BASE/webhook/gumroad"
  curl -sS -H "Content-Type: application/json" -H "X-Gumroad-Signature: $SIG" -d "$BODY" "$URL_BASE/webhook/gumroad" || true
fi

rm -f /tmp/telegram_update.json

echo "dev_test.sh finished"
