import logging
import html
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database_manager import get_user_credits, deduct_credit, get_user_profile, add_xp
from database_manager import register_user_if_not_exists
from database_manager import add_credits_from_gumroad
from ai_handler import get_ai_response
import uuid

logger = logging.getLogger(__name__)

# --- MENUS ---
MAIN_MENU = [
    [KeyboardButton("🚀 Mi Ruta de Aprendizaje"), KeyboardButton("🧪 Laboratorios Prácticos")],
    [KeyboardButton("🏆 Desafíos & CTFs"), KeyboardButton("💎 Zona Premium")],
    [KeyboardButton("👥 Comunidad"), KeyboardButton("⚙️ Mi Cuenta")]
]

LEARNING_MENU = [
    [KeyboardButton("📚 Módulos"), KeyboardButton("📊 Mi Progreso")],
    [KeyboardButton("🎓 Mis Certificados"), KeyboardButton("🔙 Volver al Menú Principal")]
]

LABS_MENU = [
    [KeyboardButton("🌐 Redes Locales"), KeyboardButton("🌍 Aplicaciones Web")],
    [KeyboardButton("📡 Wi-Fi"), KeyboardButton("⚙️ Post-Explotación")],
    [KeyboardButton("🔙 Volver al Menú Principal")]
]

CHALLENGES_MENU = [
    [KeyboardButton("🥇 Desafío Semanal"), KeyboardButton("🏅 Ranking Global")],
    [KeyboardButton("🗓️ CTFs Anteriores"), KeyboardButton("🔙 Volver al Menú Principal")]
]

PREMIUM_MENU = [
    [KeyboardButton("🚀 Ver Planes de Suscripción"), KeyboardButton("🎁 Contenido Exclusivo")],
    [KeyboardButton("💬 Preguntas Frecuentes"), KeyboardButton("🔙 Volver al Menú Principal")]
]

COMMUNITY_MENU = [
    [KeyboardButton("💬 Chat de la Comunidad"), KeyboardButton("📢 Canal de Novedades")],
    [KeyboardButton("🆘 Pide Ayuda"), KeyboardButton("🔙 Volver al Menú Principal")]
]

ACCOUNT_MENU = [
    [KeyboardButton("📈 Estadísticas Personales"), KeyboardButton("🏆 Mis Insignias")],
    [KeyboardButton("🔑 Gestionar Suscripción"), KeyboardButton("📩 Contactar Soporte")],
    [KeyboardButton("🔙 Volver al Menú Principal")]
]

async def send_menu(update: Update, text: str, menu: list):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True),
        parse_mode=ParseMode.HTML
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return

    logger.info(f"Received message from {user_id}: {text}")

    # --- COMMANDS ---
    if text.strip().split()[0].startswith("/start"):
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        username = update.effective_user.username
        await register_user_if_not_exists(user_id, first_name=first_name, last_name=last_name, username=username)
        
        welcome_msg = (
            f"¡Bienvenido, <b>{html.escape(first_name or 'Hacker')}</b>! 🕵️‍♂️\n\n"
            "Soy tu mentor en <b>Kali Linux</b>. Estás a punto de empezar un viaje para dominar las herramientas de los profesionales.\n\n"
            "¿Listo para desbloquear tu potencial? Elige tu camino:"
        )
        await send_menu(update, welcome_msg, MAIN_MENU)
        return

    if text == "/comprar":
        enlace = f"https://gumroad.com/l/pack-100-creditos?custom_fields=telegram_user_id:{user_id}&uuid={uuid.uuid4()}"
        href = html.escape(enlace)
        await update.message.reply_text(f"Compra créditos aquí: <a href=\"{href}\">Abrir enlace</a>", parse_mode=ParseMode.HTML)
        return

    if text == "/saldo":
        credits = await get_user_credits(user_id)
        await update.message.reply_text(f"Su saldo actual es: <b>{credits}</b> créditos.", parse_mode=ParseMode.HTML)
        return

    # --- MENU NAVIGATION ---
    if text == "🔙 Volver al Menú Principal":
        await send_menu(update, "Regresando al cuartel general...", MAIN_MENU)
        return

    # 1. Ruta de Aprendizaje
    if text == "🚀 Mi Ruta de Aprendizaje":
        await send_menu(update, "Tu progreso es tu mapa hacia la maestría. 🗺️", LEARNING_MENU)
        return
    
    if text == "📚 Módulos":
        msg = (
            "<b>Módulos Disponibles:</b>\n\n"
            "✅ <b>Módulo 1: Fundamentos</b> (Completado)\n"
            "🟡 <b>Módulo 2: Reconocimiento</b> (En curso)\n"
            "🔒 <b>Módulo 3: Escaneo</b> (Bloqueado)\n\n"
            "<i>¡Sigue estudiando para desbloquear más!</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # 2. Laboratorios
    if text == "🧪 Laboratorios Prácticos":
        await send_menu(update, "Aquí es donde se forjan las habilidades reales. 🔥", LABS_MENU)
        return

    if text == "🌐 Redes Locales":
        # Simulación de completar un lab
        await update.message.reply_text("Iniciando Lab: <b>Escaneo de Red Local</b>... 🖥️", parse_mode=ParseMode.HTML)
        # Simular recompensa (esto debería ser tras completar el lab real)
        xp_res = await add_xp(user_id, 50)
        if xp_res.get('success'):
            await update.message.reply_text(f"¡Excelente! Has ganado <b>50 XP</b>. Total: {xp_res.get('total_xp')} XP.", parse_mode=ParseMode.HTML)
        return

    # 3. Desafíos
    if text == "🏆 Desafíos & CTFs":
        await send_menu(update, "¡Demuestra tu valía en la arena! ⚔️", CHALLENGES_MENU)
        return

    # 4. Premium
    if text == "💎 Zona Premium":
        await send_menu(update, "Accede al conocimiento de élite. 💎", PREMIUM_MENU)
        return

    # 5. Comunidad
    if text == "👥 Comunidad":
        await send_menu(update, "No estás solo en este viaje. 🤝", COMMUNITY_MENU)
        return

    # 6. Mi Cuenta
    if text == "⚙️ Mi Cuenta":
        await send_menu(update, "Tus estadísticas y logros. 📊", ACCOUNT_MENU)
        return

    if text == "📈 Estadísticas Personales":
        profile = await get_user_profile(user_id)
        if profile:
            msg = (
                f"👤 <b>Perfil de Hacker:</b>\n\n"
                f"🏅 <b>Nivel:</b> {profile.get('level', 1)}\n"
                f"✨ <b>XP:</b> {profile.get('xp', 0)}\n"
                f"🔥 <b>Racha:</b> {profile.get('streak_days', 0)} días\n"
                f"💳 <b>Créditos:</b> {profile.get('credit_balance', 0)}\n"
                f"🎖 <b>Rango:</b> {profile.get('subscription_tier', 'Novato').title()}"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("Error al cargar perfil.", parse_mode=ParseMode.HTML)
        return

    # --- AI FALLBACK ---
    # Si no es un comando de menú, asumimos que es una pregunta para la IA
    credits = await get_user_credits(user_id)
    if credits == 0:
        await update.message.reply_text("Saldo insuficiente. Use /comprar para adquirir más créditos.", parse_mode=ParseMode.HTML)
        return

    await update.message.reply_text("Analizando tu consulta... 🤖", parse_mode=ParseMode.HTML)
    try:
        respuesta = await get_ai_response(text)
        from config import FALLBACK_AI_TEXT
        if not respuesta or respuesta.strip() == FALLBACK_AI_TEXT.strip():
            await update.message.reply_text(FALLBACK_AI_TEXT, parse_mode=ParseMode.HTML)
            return

        success = await deduct_credit(user_id)
        if success:
            await update.message.reply_text(f"<b>Respuesta:</b>\n{respuesta}", parse_mode=ParseMode.HTML)
            # Dar un poco de XP por usar el bot
            await add_xp(user_id, 5) 
        else:
            await update.message.reply_text("Error al procesar créditos.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception("Error procesando mensaje AI")
        await update.message.reply_text("Ocurrió un error inesperado.", parse_mode=ParseMode.HTML)
