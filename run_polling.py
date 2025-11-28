#!/usr/bin/env python3
"""
Run the bot in polling mode for local development. This script uses the Application builder and
registers the `handle_message` message handler for simple testing.
"""
import logging
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from bot_logic import handle_message
from config import TELEGRAM_BOT_TOKEN
import sys
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

def run():
    # Validate TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.strip().lower() in ('', 'your-telegram-bot-token-here'):
        logger.error("TELEGRAM_BOT_TOKEN no está configurado o tiene un placeholder. Establece TELEGRAM_BOT_TOKEN en tu .env o exportándolo antes de ejecutar el script.")
        logger.error("Puedes probar el token: curl https://api.telegram.org/bot<token>/getMe")
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    # If a webhook is configured this may cause a Conflict error with getUpdates.
    # If DELETE_WEBHOOK_ON_POLLING is True, delete any configured webhook before polling.
    from config import DELETE_WEBHOOK_ON_POLLING
    if DELETE_WEBHOOK_ON_POLLING:
        try:
            logger.info("Checking webhook info before starting polling (synchronous check)...")
            # Use a synchronous HTTP call to Telegram API rather than calling bot internals
            import json
            from urllib.request import urlopen, Request
            get_webhook_info = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            req = Request(get_webhook_info)
            with urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            webhook_info = data.get('result', {}) if isinstance(data, dict) else {}
            url = webhook_info.get('url')
            if url:
                logger.warning('Webhook detected: %s', url)
                logger.info('Deleting existing webhook to allow polling to run...')
                delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
                req2 = Request(delete_url)
                with urlopen(req2, timeout=5) as resp2:
                    data2 = json.loads(resp2.read())
                if data2.get('ok'):
                    logger.info('Deleted webhook successfully (drop_pending_updates=True)')
                else:
                    logger.warning('deleteWebhook returned non-ok response: %s', data2)
        except Exception as e:
            logger.exception('Failed to inspect/delete webhook automatically: %s', e)
    app.add_handler(CommandHandler('start', handle_message))
    app.add_handler(CommandHandler('comprar', handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    run()
