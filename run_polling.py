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
    app.add_handler(CommandHandler('start', handle_message))
    app.add_handler(CommandHandler('comprar', handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    run()
