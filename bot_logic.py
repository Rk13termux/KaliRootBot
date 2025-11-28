import logging
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database_manager import get_user_credits, deduct_credit
from database_manager import register_user_if_not_exists
from database_manager import add_credits_from_gumroad
from ai_handler import get_ai_response
import uuid

logger = logging.getLogger(__name__)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    logger.debug(f"handle_message: user_id={user_id}, text={text}, from={update.effective_user}")
    # Only register user when they send /start, and only if they're new
    logger.info(f"Received message from {user_id}: {text}")
    if text and text.strip().split()[0].startswith("/start"):
        logger.debug(f"Detected /start command in message: {text}")
        try:
            first_name = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else None
            last_name = update.effective_user.last_name if update.effective_user and update.effective_user.last_name else None
            username = update.effective_user.username if update.effective_user and update.effective_user.username else None
            logger.debug(f"Calling register_user_if_not_exists with first_name={first_name}, last_name={last_name}, username={username}")
            created = await register_user_if_not_exists(user_id, first_name=first_name, last_name=last_name, username=username)
            logger.debug(f"register_user_if_not_exists returned: {created}")
            if created:
                await update.message.reply_text("Bienvenido a Kali Tutor Bot. Su registro se ha realizado correctamente. Use /comprar para adquirir créditos y haga sus consultas sobre Kali Linux.", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("Bienvenido de nuevo a Kali Tutor Bot. Use /comprar para adquirir créditos y haga sus consultas sobre Kali Linux.", parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.exception("Failed to register user during /start: %s", e)
            await update.message.reply_text("Bienvenido a Kali Tutor Bot! Usa /comprar para adquirir créditos y pregunta lo que quieras sobre Kali Linux.")
        return
    if text == "/comprar":
        enlace = f"https://gumroad.com/l/pack-100-creditos?custom_fields=telegram_user_id:{user_id}&uuid={uuid.uuid4()}"
        # Use <a> for a clickable link in Telegram's HTML format and a code fallback
        href = html.escape(enlace)
        await update.message.reply_text(f"Compra créditos aquí: <a href=\"{href}\">Abrir enlace</a>\n<code>{html.escape(enlace)}</code>", parse_mode=ParseMode.HTML)
        return
    if text == "/saldo":
        credits = await get_user_credits(user_id)
        await update.message.reply_text(f"Su saldo actual es: <b>{credits}</b> créditos.", parse_mode=ParseMode.HTML)
        return
    credits = await get_user_credits(user_id)
    if credits == 0:
        await update.message.reply_text("Saldo insuficiente. Use /comprar para adquirir más créditos.", parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text("Procesando su petición...", parse_mode=ParseMode.HTML)
    try:
        respuesta = await get_ai_response(text)
        if not respuesta:
            logger.warning('AI returned empty response; not charging credit and informing user')
            await update.message.reply_text("Lo siento, no pude generar una respuesta. Intente de nuevo más tarde.", parse_mode=ParseMode.HTML)
            return
        # If respuesta is equal to the fallback text, treat as a failure and do not charge
        from config import FALLBACK_AI_TEXT
        if respuesta.strip() == FALLBACK_AI_TEXT.strip():
            logger.warning('AI returned fallback response; not charging credit and informing user')
            await update.message.reply_text(FALLBACK_AI_TEXT, parse_mode=ParseMode.HTML)
            return
        # Only deduct credit if we have a valid respuesta
        success = await deduct_credit(user_id)
        logger.info(f"User {user_id} had {credits} credits. Deduct success: {success}")
        if success:
            # The AI response is already formatted as HTML in get_ai_response; prefix it with a short label
            await update.message.reply_text(f"<b>Respuesta:</b> {respuesta}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("No se pudo descontar el crédito. Intente de nuevo más tarde.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception("Error procesando mensaje:")
        await update.message.reply_text(f"Error procesando su petición: <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
