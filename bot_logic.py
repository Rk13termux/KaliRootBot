import logging
import requests  # Added for URL validation
import html
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from database_manager import get_user_credits, deduct_credit, get_user_profile, register_user_if_not_exists, is_user_subscribed, set_subscription_pending, add_xp
from learning_manager import get_user_learning, add_experience, complete_lesson
from ai_handler import get_ai_response
from nowpayments_handler import create_payment_invoice
from config import TELEGRAM_WEBHOOK_URL
import uuid

logger = logging.getLogger(__name__)
import asyncio

def is_url_valid(url: str) -> bool:
    """Check if a URL is reachable (status < 400). Returns False on exceptions."""
    if not url: return False
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        return response.status_code < 400
    except Exception:
        return False

# --- MENUS ---
# Menú para usuarios FREE (más persuasivo para convertir a Premium)
MAIN_MENU_FREE = [
    [KeyboardButton("💎 DESBLOQUEAR PREMIUM")],
    [KeyboardButton("🤖 Asistente IA"), KeyboardButton("⚙️ Mi Cuenta")],
    [KeyboardButton("👥 Comunidad"), KeyboardButton("🛠️ Tools")],
    [KeyboardButton("🛒 Tienda / Recargas")]
]

# Menú para usuarios PREMIUM (experiencia limpia)
# El Dashboard se abre via InlineKeyboardButton en el mensaje de bienvenida
MAIN_MENU_PREMIUM = [
    [KeyboardButton("⚙️ Mi Cuenta"), KeyboardButton("📞 Soporte VIP")]
]

# Backward compatibility
MAIN_MENU = MAIN_MENU_FREE

TOOLS_MENU = [
    [KeyboardButton("🌐 Web Tools"), KeyboardButton("📄 PDF Tools")],
    [KeyboardButton("📦 Repositorios"), KeyboardButton("📜 Scripts")],
    [KeyboardButton("📱 Termux"), KeyboardButton("🔙 Volver al Menú Principal")]
]


# LEARNING_MENU removed - Learning system now uses WebApp

# LABS_MENU removed - Labs system now uses WebApp


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

async def get_premium_dashboard_keyboard(user_id: int):
    """Genera el InlineKeyboard con botón de Dashboard para usuarios premium."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    base_url = TELEGRAM_WEBHOOK_URL.replace("/webhook/telegram", "") if TELEGRAM_WEBHOOK_URL else ""
    keyboard = []
    if base_url:
        from token_manager import generate_session_token
        token = generate_session_token(user_id, is_premium=True)
        webapp_url = f"{base_url}/webapp/dashboard?token={token}"
        keyboard = [[InlineKeyboardButton("🚀 Abrir Dashboard", web_app=WebAppInfo(url=webapp_url))]]
    return InlineKeyboardMarkup(keyboard) if keyboard else None

async def send_premium_redirect(update: Update, user_id: int, custom_message: str = None):
    """Envía mensaje recordando al usuario premium que use el Dashboard."""
    keyboard = await get_premium_dashboard_keyboard(user_id)
    msg = custom_message or (
        "👑 <b>Función Premium</b>\n\n"
        "Esta función está disponible en tu Dashboard.\n"
        "Toca el botón para acceder:"
    )
    await update.message.reply_text(
        msg,
        reply_markup=keyboard if keyboard else ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )

async def clean_trigger_message(update: Update):
    """
    Disabled: Chat cleaning is turned off.
    """
    return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return

    logger.info(f"Received message from {user_id}: {text}")

    # --- COMMANDS ---
    if text.strip().split()[0].startswith("/start"):
        # Delete the /start message from user to keep chat clean
        try:
            await update.message.delete()
        except Exception as e:
            logger.debug(f"Could not delete /start message: {e}")
        
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        username = update.effective_user.username
        await register_user_if_not_exists(user_id, first_name=first_name, last_name=last_name, username=username)
        
        # Check if user is Premium
        is_premium = await is_user_subscribed(user_id)
        
        if is_premium:
            # ===== MENSAJE DE BIENVENIDA PREMIUM =====
            # Primero removemos el ReplyKeyboard enviando un mensaje temporal
            cleanup_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Cargando tu experiencia Premium...",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Eliminar el mensaje de limpieza
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id, 
                    message_id=cleanup_msg.message_id
                )
            except Exception as e:
                logger.debug(f"Could not delete cleanup message: {e}")
            
            welcome_msg = (
                f"👑 <b>¡Bienvenido, {html.escape(first_name or 'Élite')}!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "💎 <b>ESTADO:</b> Suscriptor Premium Activo ✅\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🚀 <b>TU ACCESO EXCLUSIVO INCLUYE:</b>\n\n"
                "▪️ 🧠 <b>IA Sin Límites</b> - Consultas ilimitadas sin censura\n"
                "▪️ 🎓 <b>Academia Hacker</b> - 100 Módulos completos\n"
                "▪️ 🧪 <b>Laboratorios</b> - Prácticas ilimitadas\n"
                "▪️ 📜 <b>Scripts VIP</b> - Recursos exclusivos\n"
                "▪️ 🏅 <b>Certificados</b> - Valida tu conocimiento\n"
                "▪️ 📞 <b>Soporte VIP</b> - Respuesta prioritaria\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎯 <b>Tu experiencia es 100% en la WebApp</b>\n"
                "Toca el botón para acceder a tu Dashboard:\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            # Botón para abrir WebApp
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
            base_url = TELEGRAM_WEBHOOK_URL.replace("/webhook/telegram", "") if TELEGRAM_WEBHOOK_URL else ""
            keyboard = []
            if base_url:
                from token_manager import generate_session_token
                token = generate_session_token(user_id, is_premium=True)
                webapp_url = f"{base_url}/webapp/dashboard?token={token}"
                keyboard = [
                    [InlineKeyboardButton("🚀 ABRIR DASHBOARD PREMIUM", web_app=WebAppInfo(url=webapp_url))],
                    [InlineKeyboardButton("📞 Soporte VIP", url="https://t.me/KaliRootHack")]
                ]
            
            # Enviar imagen premium
            try:
                with open('assets/welcome_premium.jpg', 'rb') as img:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img,
                        caption=welcome_msg,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                        parse_mode=ParseMode.HTML
                    )
            except FileNotFoundError:
                logger.warning("Premium welcome image not found, sending text only")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Error sending premium welcome: {e}")
                # Fallback: enviar mensaje de texto simple
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                    parse_mode=ParseMode.HTML
                )
        else:
            # ===== MENSAJE DE BIENVENIDA FREE =====
            welcome_msg = (
                f"👋 <b>¡Hola, {html.escape(first_name or 'Agente')}!</b>\n\n"
                "Bienvenido a <b>KaliRoot Bot</b> 🔒\n"
                "Tu asistente de ciberseguridad con IA.\n\n"
                
                "⚡ <b>PLAN GRATUITO:</b>\n"
                "▫️ 🤖 Asistente IA (3 consultas/día)\n"
                "▫️ 🛠️ Herramientas básicas\n"
                "▫️ 👥 Comunidad pública\n\n"
                
                "💎 <b>¿QUIERES MÁS?</b>\n"
                "Con <b>Premium ($10/mes)</b> obtienes:\n"
                "✅ IA sin límites ni censura\n"
                "✅ 100 Laboratorios de hacking real\n"
                "✅ Academia completa Zero to Hero\n"
                "✅ Certificados oficiales\n"
                "✅ +250 créditos IA mensuales\n\n"
                
                "🔥 <b>¡Los primeros 100 usuarios tienen 50% OFF!</b>\n\n"
                "👇 Escribe tu pregunta o usa el menú:"
            )
            
            # Enviar imagen free
            try:
                with open('assets/welcome.jpg', 'rb') as img:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img,
                        caption=welcome_msg,
                        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_FREE, resize_keyboard=True),
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending welcome image: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_msg,
                    reply_markup=ReplyKeyboardMarkup(MAIN_MENU_FREE, resize_keyboard=True),
                    parse_mode=ParseMode.HTML
                )
        return

    if text == "/suscribirse" or text == "/comprar" or text == "🚀 Ver Planes de Suscripción":
        # No cleaning here
        # Create invoice
        amount = 10.0 # USD
        invoice = create_payment_invoice(amount, user_id)
        
        if invoice and invoice.get('invoice_url'):
            await set_subscription_pending(user_id, invoice.get('invoice_id'))
            msg = (
                f"<b>💎 Suscripción Premium</b>\n\n"
                f"Accede a todo el contenido exclusivo por solo <b>${amount} USD</b> al mes.\n\n"
                f"👉 <a href=\"{invoice['invoice_url']}\">Haz clic aquí para pagar con Criptomonedas (USDT/TRC20)</a>\n\n"
                "<i>Tu suscripción se activará automáticamente una vez confirmado el pago.</i>"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("Error al generar la factura. Por favor intenta más tarde.", parse_mode=ParseMode.HTML)
        return

    if text == "/saldo":
        # No cleaning here
        credits = await get_user_credits(user_id)
        await update.message.reply_text(f"Su saldo actual es: <b>{credits}</b> créditos.", parse_mode=ParseMode.HTML)
        return

    # --- MENU NAVIGATION ---
    if text == "🔙 Volver al Menú Principal":
        # Verificar si el usuario es premium para mostrar el menú correcto
        is_premium = await is_user_subscribed(user_id)
        if is_premium:
            await send_premium_redirect(
                update,
                user_id,
                "👑 <b>Eres usuario Premium</b>\n\n"
                "Tu experiencia completa está en el Dashboard.\n"
                "Toca el botón para acceder:"
            )
        else:
            await send_menu(update, "Regresando al cuartel general...", MAIN_MENU_FREE)
        return
    
    # Handler para el botón de desbloquear premium
    if text == "💎 DESBLOQUEAR PREMIUM":
        from nowpayments_handler import create_payment_invoice
        from database_manager import set_subscription_pending
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        inv_sub = create_payment_invoice(10.0, user_id, "subscription")
        
        msg = (
            "💎 <b>DESBLOQUEA TODO EL PODER</b>\n\n"
            "Únete a la élite de hackers y obtén acceso ilimitado:\n\n"
            "🚀 <b>BENEFICIOS PREMIUM:</b>\n"
            "✅ <b>IA Sin Límites</b> - Consultas ilimitadas sin censura\n"
            "✅ <b>100 Laboratorios</b> - Hacking real paso a paso\n"
            "✅ <b>Academia Completa</b> - De cero a profesional\n"
            "✅ <b>WebApp Exclusiva</b> - Dashboard personalizado\n"
            "✅ <b>Certificados</b> - Valida tu conocimiento\n"
            "✅ <b>+250 Créditos/Mes</b> - Bonus automático\n"
            "✅ <b>Soporte VIP</b> - Respuesta prioritaria\n\n"
            "💰 <b>PRECIO:</b> Solo $10 USD/mes\n\n"
            "🔥 <b>OFERTA LIMITADA:</b> ¡50% OFF primeros 100 usuarios!\n\n"
            "👇 <b>Activa ahora con criptomonedas:</b>"
        )
        
        keyboard = []
        if inv_sub and inv_sub.get('invoice_url') and is_url_valid(inv_sub['invoice_url']):
            await set_subscription_pending(user_id, inv_sub.get('invoice_id'))
            keyboard.append([InlineKeyboardButton("🚀 ACTIVAR PREMIUM ($10)", url=inv_sub['invoice_url'])])
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode=ParseMode.HTML)
        return
    
    # Handler para Asistente IA (diferenciado Free/Premium)
    if text == "🤖 Asistente IA":
        is_premium = await is_user_subscribed(user_id)
        
        if is_premium:
            msg = (
                "🧠 <b>ASISTENTE IA PREMIUM</b> 👑\n\n"
                "Tienes acceso <b>ILIMITADO</b> a la IA sin censura.\n\n"
                "📌 <b>Puedes preguntarme:</b>\n"
                "• Scripts avanzados de pentesting\n"
                "• Técnicas de hacking y bypass\n"
                "• Análisis de malware\n"
                "• Cualquier tema de ciberseguridad\n\n"
                "✨ <b>Sin límites. Sin restricciones.</b>\n\n"
                "👇 <b>Escribe tu pregunta:</b>"
            )
        else:
            msg = (
                "🤖 <b>ASISTENTE IA KALIROOT</b>\n\n"
                "Escríbeme tu pregunta sobre ciberseguridad.\n\n"
                "📌 <b>Ejemplos:</b>\n"
                "• ¿Cómo usar Nmap para escanear puertos?\n"
                "• ¿Qué es SQL Injection?\n"
                "• Dame un script para OSINT\n\n"
                "⚠️ <b>Plan Free:</b> 3 consultas/día\n"
                "💎 <b>Premium:</b> Consultas ilimitadas\n\n"
                "👇 <b>Escribe tu pregunta:</b>"
            )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # --- TOOLS MENU ---
    if text == "🛠️ Tools":
        await send_menu(update, "🛠️ <b>ARSENAL DE HERRAMIENTAS</b>\n\nSelecciona una categoría para acceder a las utilidades:", TOOLS_MENU)
        return

    if text == "🌐 Web Tools":
        msg = (
            "🌐 <b>WEB TOOLS</b>\n\n"
            "Herramientas para análisis y reconocimiento web:\n"
            "• <b>Whois Lookup</b>: Información de dominios\n"
            "• <b>DNS Enumeration</b>: Mapeo de subdominios\n"
            "• <b>HTTP Headers</b>: Análisis de cabeceras\n\n"
            "<i>(Próximamente más herramientas interactivas)</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if text == "📄 PDF Tools":
        msg = (
            "📄 <b>PDF TOOLS</b>\n\n"
            "Utilidades para manipulación de documentos:\n"
            "• <b>Metadatos</b>: Extracción de info oculta\n"
            "• <b>Crack PDF</b>: Fuerza bruta de contraseñas\n"
            "• <b>Watermark</b>: Añadir marcas de agua\n\n"
            "<i>(Sube un archivo PDF para analizarlo - Próximamente)</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if text == "📦 Repositorios":
        msg = (
            "📦 <b>REPOSITORIOS ESENCIALES</b>\n\n"
            "Colección curada de repositorios de GitHub para hackers:\n\n"
            "🔹 <a href='https://github.com/swisskyrepo/PayloadsAllTheThings'>PayloadsAllTheThings</a>\n"
            "🔹 <a href='https://github.com/danielmiessler/SecLists'>SecLists</a>\n"
            "🔹 <a href='https://github.com/carlospolop/PEASS-ng'>PEASS-ng (Privilege Escalation)</a>\n"
            "🔹 <a href='https://github.com/sqlmapproject/sqlmap'>SQLMap</a>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return

    if text == "📜 Scripts":
        msg = (
            "📜 <b>SCRIPTS DE AUTOMATIZACIÓN</b>\n\n"
            "Scripts útiles para tareas comunes:\n"
            "• <b>Nmap Automator</b>: Escaneo rápido\n"
            "• <b>AutoRecon</b>: Reconocimiento masivo\n"
            "• <b>LinEnum</b>: Enumeración local Linux\n\n"
            "<i>(Próximamente descarga directa de scripts)</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if text == "📱 Termux":
        msg = (
            "📱 <b>TERMUX ELITE ZONE</b>\n\n"
            "Bienvenido al arsenal de bolsillo. Aquí dominamos Android como un arma.\n\n"
            "🔥 <b>RECURSOS ESENCIALES:</b>\n"
            "• <b>Termux-API</b>: Controla hardware (cámara, GPS, SMS)\n"
            "• <b>Proot-Distro</b>: Instala Kali/Ubuntu en Termux\n"
            "• <b>Termux-Styling</b>: Personaliza tu terminal\n\n"
            "💡 <i>Tip: Pídeme cualquier comando o script para Termux. Conozco la Wiki de memoria.</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # LIMPIAR CHAT - Eliminado (ya no está en el menú)
    # El callback aún existe por compatibilidad
    if text == "🧹 Limpiar Chat":
        await update.message.reply_text("Esta función ha sido removida. Usa /start para reiniciar.", parse_mode=ParseMode.HTML)
        return
    
    # Soporte VIP (para usuarios premium)
    if text == "📞 Soporte VIP":
        support_username = "KaliRootHack"
        msg = (
            "👑 <b>SOPORTE VIP PREMIUM</b>\n\n"
            "Como miembro Premium, tienes acceso a soporte prioritario.\n\n"
            "📞 <b>Canal directo:</b> Respuesta en menos de 2 horas\n"
            "🛠️ <b>Ayuda técnica:</b> Resolución de problemas\n"
            "💡 <b>Asesoría:</b> Orientación personalizada\n\n"
            "👇 <b>Toca para contactar:</b>"
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        support_url = f"https://t.me/{support_username}"
        keyboard = [[InlineKeyboardButton("💬 Contactar Soporte VIP", url=support_url)]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    # Learning system is now only available through the Premium WebApp
    # Removed the bot-based learning handler


    # Labs system is now only available through the WebApp
    
    # 3. Desafíos (Moved to WebApp or removed)

    # 4. Premium
    if text == "💎 Zona Premium":
        await send_menu(update, "Accede al conocimiento de élite. 💎", PREMIUM_MENU)
        return

    if text == "🎁 Contenido Exclusivo":
        if not await is_user_subscribed(user_id):
            await update.message.reply_text("🔒 <b>Contenido Bloqueado</b>\n\nEste contenido es exclusivo para suscriptores Premium. Usa /suscribirse para acceder.", parse_mode=ParseMode.HTML)
            return
        
        await update.message.reply_text("🔓 <b>Bienvenido a la Zona VIP</b>\n\nAquí tienes tus herramientas exclusivas...", parse_mode=ParseMode.HTML)
        return

    # 5. Comunidad (Reemplazado por Soporte Directo o mantenemos menú?)
    # El usuario pidió "en contactar soporte abra alguna forma de que el boton los envie a un chat privado"
    # Asumo que se refiere a la opción del menú principal o un submenú.
    # Si "📞 Contactar Soporte" es una opción, la manejamos aquí.
    
    if text == "📩 Contactar Soporte" or text == "📞 Contactar Soporte":
        # Reemplaza 'TuUsuarioDeSoporte' con tu username real sin @
        support_username = "KaliRootHack" 
        
        msg = (
            "<b>🆘 CENTRO DE SOPORTE</b>\n\n"
            "¿Tienes problemas con tu suscripción o necesitas ayuda técnica?\n\n"
            "Habla directamente con un administrador humano. Estamos aquí para ayudarte a dominar el sistema."
        )
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        support_url = f"https://t.me/{support_username}"
        keyboard = []
        if is_url_valid(support_url):
            keyboard = [[InlineKeyboardButton("💬 Abrir Chat con Soporte", url=support_url)]]

        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            parse_mode=ParseMode.HTML
        )
        return

    if text == "👥 Comunidad":
         await send_menu(update, "No estás solo en este viaje. 🤝", COMMUNITY_MENU)
         return

    if text == "🏆 Mis Insignias":
        from database_manager import get_user_badges
        badges = await get_user_badges(user_id)
        
        if not badges:
            await update.message.reply_text("Todavía no tienes insignias. ¡Completa módulos y usa el bot para ganarlas! 🎖️", parse_mode=ParseMode.HTML)
            return
            
        msg = "<b>🏆 TUS INSIGNIAS:</b>\n\n"
        for b in badges:
            msg += f"{b['icon']} <b>{b['name']}</b>\n<i>{b['description']}</i>\n\n"
            
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # 6. Mi Cuenta
    if text == "⚙️ Mi Cuenta":
        is_premium = await is_user_subscribed(user_id)
        if is_premium:
            # Usuarios premium ven su cuenta en el Dashboard
            await send_premium_redirect(
                update, 
                user_id,
                "👑 <b>Mi Cuenta Premium</b>\n\n"
                "Gestiona tu cuenta, estadísticas y suscripción\n"
                "directamente desde tu Dashboard:\n"
            )
        else:
            await send_menu(update, "Tus estadísticas y logros. 📊", ACCOUNT_MENU)
        return

    # 7. Tienda / Recargas (NUEVO SISTEMA)
    if text == "🛒 Tienda / Recargas" or text == "/tienda":
        is_subscribed = await is_user_subscribed(user_id)
        
        # Definir menú dinámico basado en suscripción
        store_menu = [[KeyboardButton("💳 Comprar Créditos")]]
        
        if not is_subscribed:
            store_menu.append([KeyboardButton("🔑 Comprar Suscripción")])
            
        store_menu.append([KeyboardButton("🔙 Volver al Menú Principal")])
        
        msg = (
            "🛒 <b>BIENVENIDO A LA TIENDA HACKER</b>\n\n"
            "Aquí puedes adquirir recursos para potenciar tu aprendizaje y herramientas.\n\n"
            "👇 <b>Selecciona una categoría:</b>"
        )
        
        await send_menu(update, msg, store_menu)
        return

    # Handler: Comprar Créditos
    if text == "💳 Comprar Créditos":
        from nowpayments_handler import create_payment_invoice
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        await update.message.reply_text("🔄 Cargando planes de créditos...", parse_mode=ParseMode.HTML)
        
        # Generar facturas
        inv_starter = create_payment_invoice(7.0, user_id, "400_credits")
        inv_pro = create_payment_invoice(14.0, user_id, "900_credits")
        inv_elite = create_payment_invoice(20.0, user_id, "1500_credits")
        
        msg = (
            "⚡ <b>RECARGA DE CRÉDITOS IA</b>\n\n"
            "Obtén potencia de cálculo para nuestra IA sin censura y herramientas avanzadas.\n\n"
            "📦 <b>PLANES DISPONIBLES:</b>\n\n"
            "🥉 <b>STARTER</b>\n"
            "├ 400 Créditos\n"
            "└ <b>$7.00 USD</b>\n\n"
            "🥈 <b>HACKER PRO</b> (+12% Extra)\n"
            "├ 900 Créditos\n"
            "└ <b>$14.00 USD</b>\n\n"
            "🥇 <b>ELITE</b> (🔥 <b>OFERTA IRRESISTIBLE</b>)\n"
            "├ <b>1500 Créditos</b> (Casi 4x el plan básico)\n"
            "└ <b>$20.00 USD</b>\n\n"
            "👇 <b>Toca el botón para pagar con Cripto (USDT):</b>"
        )
        
        keyboard = []
        if inv_starter and inv_starter.get('invoice_url') and is_url_valid(inv_starter['invoice_url']):
            keyboard.append([InlineKeyboardButton("🥉 Comprar Starter ($7)", url=inv_starter['invoice_url'])])
        if inv_pro and inv_pro.get('invoice_url') and is_url_valid(inv_pro['invoice_url']):
            keyboard.append([InlineKeyboardButton("🥈 Comprar Hacker Pro ($14)", url=inv_pro['invoice_url'])])
        if inv_elite and inv_elite.get('invoice_url') and is_url_valid(inv_elite['invoice_url']):
            keyboard.append([InlineKeyboardButton("🥇 Comprar Elite ($20)", url=inv_elite['invoice_url'])])
        
        if not keyboard:
            await update.message.reply_text("⚠️ Error de conexión con pagos. Intenta más tarde.", parse_mode=ParseMode.HTML)
            return
            
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    # Handler: Comprar Suscripción
    if text == "🔑 Comprar Suscripción":
        # Verificar de nuevo por si acaso
        if await is_user_subscribed(user_id):
            await update.message.reply_text("✅ ¡Ya tienes una suscripción activa!", parse_mode=ParseMode.HTML)
            return

        from nowpayments_handler import create_payment_invoice
        from database_manager import set_subscription_pending
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        await update.message.reply_text("🔄 Generando oferta de suscripción...", parse_mode=ParseMode.HTML)
        
        inv_sub = create_payment_invoice(10.0, user_id, "subscription")
        
        msg = (
            "💎 <b>SUSCRIPCIÓN PREMIUM KALI ROOT</b>\n\n"
            "Desbloquea el potencial completo de la plataforma y conviértete en un profesional.\n\n"
            "🚀 <b>BENEFICIOS INCLUIDOS:</b>\n"
            "✅ <b>Acceso Total</b> a los 100 Laboratorios Prácticos\n"
            "✅ <b>Certificados Oficiales</b> al completar módulos\n"
            "✅ <b>+250 Créditos IA</b> mensuales de regalo\n"
            "✅ <b>Soporte Prioritario</b> directo\n"
            "✅ <b>Insignias Exclusivas</b> en tu perfil\n\n"
            "🏷 <b>PRECIO:</b> $10.00 USD / Mes\n\n"
            "👇 <b>Únete a la élite ahora:</b>"
        )
        
        keyboard = []
        if inv_sub and inv_sub.get('invoice_url') and is_url_valid(inv_sub['invoice_url']):
            await set_subscription_pending(user_id, inv_sub.get('invoice_id'))
            keyboard.append([InlineKeyboardButton("🚀 Activar Premium ($10/mes)", url=inv_sub['invoice_url'])])
        else:
            await update.message.reply_text("⚠️ Error de conexión con pagos.", parse_mode=ParseMode.HTML)
            return
            
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    # Handler: Gestionar Suscripción
    if text == "🔑 Gestionar Suscripción":
        is_sub = await is_user_subscribed(user_id)
        
        if is_sub:
            # Usuario Suscrito
            msg = (
                "✅ <b>SUSCRIPCIÓN ACTIVA</b>\n\n"
                "👤 <b>Estado:</b> Premium Member 💎\n"
                "📅 <b>Renovación:</b> Automática (Mensual)\n"
                "✨ <b>Beneficios Activos:</b>\n"
                "• Acceso Total a Laboratorios\n"
                "• Certificados Habilitados\n"
                "• Bonus de Créditos IA\n\n"
                "<i>Gracias por apoyar el proyecto y tu educación.</i>"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            # Usuario NO Suscrito
            from nowpayments_handler import create_payment_invoice
            from database_manager import set_subscription_pending
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Generar factura para facilitar la suscripción inmediata
            inv_sub = create_payment_invoice(10.0, user_id, "subscription")
            
            msg = (
                "❌ <b>SUSCRIPCIÓN INACTIVA</b>\n\n"
                "Actualmente estás en el plan <b>Gratuito</b>.\n\n"
                "⚠️ <b>Limitaciones actuales:</b>\n"
                "• Acceso restringido a laboratorios avanzados\n"
                "• Sin certificados oficiales\n"
                "• Créditos de IA limitados\n\n"
                "🚀 <b>¡Sube de nivel hoy mismo!</b>"
            )
            
            keyboard = []
            if inv_sub and inv_sub.get('invoice_url') and is_url_valid(inv_sub['invoice_url']):
                await set_subscription_pending(user_id, inv_sub.get('invoice_id'))
                keyboard.append([InlineKeyboardButton("💎 Activar Premium ($10/mes)", url=inv_sub['invoice_url'])])
            else:
                support_url = "https://t.me/KaliRootSupport"
                if is_url_valid(support_url):
                    keyboard.append([InlineKeyboardButton("📞 Contactar Soporte", url=support_url)])
                
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode=ParseMode.HTML)
        return

    if text == "📈 Estadísticas Personales":
        from database_manager import get_user_profile, get_user_completed_modules
        from gamification_manager import generate_user_stats_chart
        import os
        
        profile = await get_user_profile(user_id)
        completed_modules = await get_user_completed_modules(user_id)
        
        # Prepare stats for chart
        stats = {
            'modules_completed': len(completed_modules),
            'ai_usage': profile.get('ai_usage_count', 0),
            'level': profile.get('level', 1),
            'xp': profile.get('xp', 0)
        }
        
        # Generate Chart
        chart_path = generate_user_stats_chart(user_id, stats)
        
        caption = (
            f"📊 <b>TUS ESTADÍSTICAS</b>\n\n"
            f"👤 <b>Hacker:</b> {update.effective_user.first_name}\n"
            f"🏅 <b>Nivel:</b> {stats['level']}\n"
            f"✨ <b>XP Total:</b> {stats['xp']}\n"
            f"📚 <b>Módulos Completados:</b> {stats['modules_completed']}\n"
            f"🤖 <b>Consultas IA:</b> {stats['ai_usage']}\n"
        )
        
        # WebApp Button
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        keyboard = []
        base_url = TELEGRAM_WEBHOOK_URL.replace("/webhook/telegram", "") if TELEGRAM_WEBHOOK_URL else ""
        
        if base_url:
            webapp_url = f"{base_url}/webapp_v2"
            keyboard = [[InlineKeyboardButton("🚀 Abrir Dashboard Web", web_app=WebAppInfo(url=webapp_url))]]
        
        if chart_path and os.path.exists(chart_path):
            await update.message.reply_photo(
                photo=open(chart_path, 'rb'), 
                caption=caption, 
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                parse_mode=ParseMode.HTML
            )
            try:
                os.remove(chart_path)
            except:
                pass
        else:
            await update.message.reply_text(
                caption, 
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                parse_mode=ParseMode.HTML
            )
        return

    # --- AI FALLBACK ---
    credits = await get_user_credits(user_id)
    is_sub = await is_user_subscribed(user_id)
    
    # Check if user has credits or subscription (subscribers still need credits but get bonus)
    if credits == 0 and not is_sub:
        from nowpayments_handler import create_payment_invoice
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Generate invoice for $7 = 400 credits (Starter)
        amount = 7.0
        invoice = create_payment_invoice(amount, user_id, description="400_credits")
        
        msg = (
            "⚠️ <b>CRÉDITOS AGOTADOS: IA BLOQUEADA</b>\n\n"
            "Has utilizado toda tu capacidad de procesamiento con nuestra IA de élite.\n\n"
            "🧠 <b>¿Por qué cobramos por la IA?</b>\n"
            "• Usamos <b>modelos avanzados sin censura</b> (Groq, LLaMA 3.1)\n"
            "• Respuestas especializadas en ciberseguridad\n"
            "• Sin límites de contenido técnico\n"
            "• Mantenimiento de servidores de alto rendimiento\n\n"
            "💰 <b>RECARGA RÁPIDA:</b>\n"
            "• $7 USD = 400 Créditos\n"
            "• $14 USD = 900 Créditos (+12% Extra)\n"
            "• $20 USD = 1500 Créditos (🔥 Oferta Irresistible)\n\n"
            "🎁 <b>BONUS:</b> Al suscribirte Premium ($10/mes) obtienes <b>+250 créditos GRATIS</b> además de acceso total.\n\n"
            "👇 <b>Elige tu opción:</b>"
        )
        
        keyboard = []
        if invoice and invoice.get('invoice_url') and is_url_valid(invoice['invoice_url']):
            keyboard.append([InlineKeyboardButton("💳 Recargar 400 Créditos ($7)", url=invoice['invoice_url'])])
            
            offer_url = f"https://t.me/{update.effective_chat.username}"
            # Note: update.effective_chat.username might be None for private chats or user's username? 
            # Actually effective_chat.username is the bot's username if it's a private chat? No, it's the user/group.
            # If it's a private chat with the bot, effective_chat is the user. 
            # The original code used this, assuming it links to something valid? 
            # If it's meant to link to the bot itself, it should be context.bot.username.
            # Assuming the intention was a valid link, we check it.
            if update.effective_chat.username:
                 offer_url = f"https://t.me/{update.effective_chat.username}"
                 if is_url_valid(offer_url):
                     keyboard.append([InlineKeyboardButton("🚀 Mejor Oferta: Premium + 250 Créditos ($10)", url=offer_url)])
        else:
            # Fallback
            support_url = "https://t.me/KaliRootSupport"
            if is_url_valid(support_url):
                keyboard.append([InlineKeyboardButton("📞 Contactar Soporte", url=support_url)])

        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode=ParseMode.HTML)
        return

    if credits == 0 and is_sub:
        # If subscribed but no credits, offer credits only
        from nowpayments_handler import create_payment_invoice
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        amount = 7.0
        invoice = create_payment_invoice(amount, user_id, description="400_credits")
        
        msg = (
            "⚠️ <b>CRÉDITOS AGOTADOS</b>\n\n"
            "Hacker Premium, has usado todos tus créditos de IA este mes.\n\n"
            "💰 <b>Recarga Express:</b>\n"
            "• $7 = 400 Créditos\n"
            "• $14 = 900 Créditos\n"
            "• $20 = 1500 Créditos (🔥 Oferta Irresistible)\n\n"
            "👇 <b>Selecciona tu paquete:</b>"
        )
        
        keyboard = []
        if invoice and invoice.get('invoice_url') and is_url_valid(invoice['invoice_url']):
            keyboard.append([InlineKeyboardButton("💳 Recargar $7 (400 Créditos)", url=invoice['invoice_url'])])
        else:
            # Fallback button if payment system fails
            support_url = "https://t.me/KaliRootSupport"
            if is_url_valid(support_url):
                keyboard.append([InlineKeyboardButton("📞 Contactar Soporte para Recarga", url=support_url)])
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode=ParseMode.HTML)
        return

    # Send typing action loop to keep connection alive
    import asyncio
    # 1. Enviar acción inmediata para feedback visual instantáneo
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    except Exception as e:
        logger.warning(f"Failed to send typing action: {e}")
    # 2. Iniciar tarea de fondo para mantener la animación
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context))
    
    try:
        respuesta = await get_ai_response(user_id, text)
        typing_task.cancel() # Stop typing animation
        
        from config import FALLBACK_AI_TEXT
        if not respuesta or respuesta.strip() == FALLBACK_AI_TEXT.strip():
            await update.message.reply_text(FALLBACK_AI_TEXT, parse_mode=ParseMode.HTML)
            return

        success = await deduct_credit(user_id)
        if success:
            # --- BUTTON PARSING LOGIC ---
            import re
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            buttons = []
            clean_response = respuesta
            seen_urls = set()

            # --- SCRIPT PARSING LOGIC ---
            script_match = re.search(r"\[\[SCRIPT:\s*(.*?)\]\]", respuesta)
            if script_match:
                filename = script_match.group(1).strip()
                # Extract the LAST code block (assuming it's the script)
                # We look for ```language ... ``` or just ``` ... ```
                code_blocks = re.findall(r"```(?:[\w+\-#]+)?\n(.*?)```", respuesta, re.DOTALL)
                
                if code_blocks:
                    script_content = code_blocks[-1] # Use the last block
                    script_id = str(uuid.uuid4())
                    SCRIPT_STORE[script_id] = {'filename': filename, 'content': script_content}
                    
                    buttons.append([InlineKeyboardButton(f"📥 Descargar {filename}", callback_data=f"dl_script_{script_id}")])
                
                # ALWAYS remove the [[SCRIPT:...]] tag from text (whether or not code was found)
                clean_response = clean_response.replace(script_match.group(0), "")


            # Find all [[BUTTON: Label | URL]] patterns
            # Regex handles optional whitespace and potential markdown/HTML noise around the tag
            matches = re.findall(r"\[\[BUTTON:\s*(.*?)\s*\|\s*(.*?)\]\]", respuesta)
            
            # Limit buttons to max 3 to avoid spam
            MAX_BUTTONS = 3
            button_count = 0
            
            if matches:
                for label, url in matches:
                    if button_count >= MAX_BUTTONS:
                        break
                        
                    # Clean URL and Label
                    # Remove any HTML tags from URL (e.g. <code>nmap</code> -> nmap)
                    url = re.sub(r'<[^>]+>', '', url).strip()
                    # Remove any surrounding quotes if present
                    url = url.strip("'\"")
                    label = label.strip()
                    
                    # Deduplicate based on URL
                    if url not in seen_urls and is_url_valid(url): # Validate URL here too!
                        buttons.append([InlineKeyboardButton(label, url=url)])
                        seen_urls.add(url)
                        button_count += 1
                
                # Remove ALL button tags from the visible text
                clean_response = re.sub(r"\[\[BUTTON:.*?\]\]", "", clean_response).strip()

            reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
            
            # Smart Chunking Logic
            MAX_LENGTH = 4000
            if len(clean_response) <= MAX_LENGTH:
                await update.message.reply_text(f"<b>Respuesta:</b>\n{clean_response}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            else:
                # Split by lines to avoid breaking inline tags like <b>
                lines = clean_response.split('\n')
                chunks = []
                current_chunk = ""
                in_pre = False
                
                for line in lines:
                    # Calculate added length (line + newline)
                    line_len = len(line) + 1
                    
                    # Check if adding this line exceeds the limit
                    if len(current_chunk) + line_len > MAX_LENGTH:
                        # Chunk is full, finalize it
                        if in_pre:
                            # If we are inside a code block, close it safely
                            chunks.append(current_chunk + "</code></pre>")
                            # Start next chunk with reopening the block
                            current_chunk = "<pre><code>" + line + "\n"
                        else:
                            chunks.append(current_chunk)
                            current_chunk = line + "\n"
                    else:
                        current_chunk += line + "\n"
                    
                    # Update <pre> state for the NEXT iteration/split check
                    # We assume <pre> tags don't nest and are well-formed by our formatter
                    if "<pre>" in line:
                        in_pre = True
                    if "</pre>" in line:
                        in_pre = False
                
                # Append the last chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Send first chunk with title
                await update.message.reply_text(f"<b>Respuesta:</b>\n{chunks[0]}", parse_mode=ParseMode.HTML)
                
                # Send middle chunks (plain, no header)
                for chunk in chunks[1:-1]:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                
                # Send last chunk with buttons (plain, no header)
                if len(chunks) > 1:
                    await update.message.reply_text(chunks[-1], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            # Award XP for using AI
            from database_manager import add_xp
            await add_xp(user_id, 5)
        else:
            await update.message.reply_text(
                "⚠️ <b>Error al procesar créditos.</b>\n\n"
                "Si este problema persiste, contacta a soporte.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        typing_task.cancel()
        logger.exception("Error procesando mensaje AI")
        try:
            await update.message.reply_text("Ocurrió un error inesperado. Por favor intenta de nuevo.", parse_mode=ParseMode.HTML)
        except:
            pass

async def keep_typing(chat_id, context):
    """Sends typing action every 4 seconds to keep connection alive."""
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Typing loop error: {e}")

SCRIPT_STORE = {}

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    # LIMPIAR CHAT - Confirmación
    if data == "confirm_clear_chat":
        try:
            # Borrar el mensaje de advertencia
            await query.message.delete()
            
            # Intentar borrar mensajes recientes (últimos 100)
            deleted_count = 0
            current_msg_id = query.message.message_id
            
            # Telegram solo permite borrar mensajes de las últimas 48 horas
            for i in range(100):
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=current_msg_id - i)
                    deleted_count += 1
                except Exception:
                    # Mensaje no existe o no se puede borrar
                    pass
            
            # Enviar mensaje de éxito y el /start
            from database_manager import register_user_if_not_exists, get_user_credits
            
            await register_user_if_not_exists(
                user_id,
                first_name=query.from_user.first_name,
                last_name=query.from_user.last_name,
                username=query.from_user.username
            )
            
            credits = await get_user_credits(user_id)
            user_name = query.from_user.first_name or "Hacker"
            
            welcome_msg = (
                f"🧹 <b>¡Chat limpiado exitosamente!</b>\n"
                f"<i>Se eliminaron aproximadamente {deleted_count} mensajes.</i>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👋 <b>¡Bienvenido de nuevo, {user_name}!</b>\n\n"
                "🐉 Soy <b>KaliRoot</b>, tu mentor de hacking ético.\n\n"
                f"💰 <b>Créditos disponibles:</b> {credits}\n\n"
                "🎯 <b>¿Qué quieres hacer?</b>\n"
                "• Aprende con <b>100 módulos</b> de hacking\n"
                "• Practica en <b>laboratorios reales</b>\n"
                "• Usa la <b>IA</b> para resolver tus dudas\n\n"
                "<i>Selecciona una opción del menú:</i>"
            )
            
            try:
                with open('assets/portada.jpg', 'rb') as img:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=img,
                        caption=welcome_msg,
                        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
                        parse_mode=ParseMode.HTML
                    )
            except Exception:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_msg,
                    reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Chat reiniciado. Usa el menú para continuar.",
                reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
            )
        return
    
    # LIMPIAR CHAT - Cancelar
    if data == "cancel_clear_chat":
        await query.message.edit_text(
            "❌ <b>Limpieza cancelada</b>\n\nTu chat permanece intacto.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Descargar script generado por IA
    if data.startswith("dl_script_"):
        script_id = data.replace("dl_script_", "")
        script_data = SCRIPT_STORE.get(script_id)
        
        if script_data:
            import os
            filename = script_data['filename']
            content = script_data['content']
            
            # Create temp file
            path = f"/tmp/{filename}"
            try:
                with open(path, "w") as f:
                    f.write(content)
                
                await query.message.reply_document(
                    document=open(path, "rb"),
                    caption=f"📜 <b>{filename}</b>\n\nGenerado por KaliRoot AI.",
                    parse_mode=ParseMode.HTML
                )
                os.remove(path)
            except Exception as e:
                logger.error(f"Error sending script: {e}")
                await query.message.reply_text("❌ Error al generar el archivo.")
        else:
            await query.message.reply_text("⚠️ El script ha expirado o no existe.")

