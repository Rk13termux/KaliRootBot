import logging
from telegram import Update
from telegram.ext import ContextTypes
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
                await update.message.reply_text("Bienvenido a Kali Tutor Bot! Te he registrado correctamente. Usa /comprar para adquirir créditos y pregunta lo que quieras sobre Kali Linux.")
            else:
                await update.message.reply_text("Bienvenido de nuevo a Kali Tutor Bot! Usa /comprar para adquirir créditos y pregunta lo que quieras sobre Kali Linux.")
        except Exception as e:
            logger.exception("Failed to register user during /start: %s", e)
            await update.message.reply_text("Bienvenido a Kali Tutor Bot! Usa /comprar para adquirir créditos y pregunta lo que quieras sobre Kali Linux.")
        return
    if text == "/comprar":
        enlace = f"https://gumroad.com/l/pack-100-creditos?custom_fields=telegram_user_id:{user_id}&uuid={uuid.uuid4()}"
        await update.message.reply_text(f"Compra créditos aquí: {enlace}")
        return
    if text == "/saldo":
        credits = await get_user_credits(user_id)
        await update.message.reply_text(f"Tu saldo actual es: {credits} créditos.")
        return
    credits = await get_user_credits(user_id)
    if credits == 0:
        await update.message.reply_text("Saldo insuficiente. Usa /comprar para adquirir más créditos.")
        return
    await update.message.reply_text("Procesando tu pregunta...")
    try:
        respuesta = await get_ai_response(text)
        success = await deduct_credit(user_id)
        logger.info(f"User {user_id} had {credits} credits. Deduct success: {success}")
        if success:
            await update.message.reply_text(respuesta)
        else:
            await update.message.reply_text("No se pudo descontar el crédito. Intenta de nuevo.")
    except Exception as e:
        logger.exception("Error procesando mensaje:")
        await update.message.reply_text(f"Error procesando tu pregunta: {str(e)}")
