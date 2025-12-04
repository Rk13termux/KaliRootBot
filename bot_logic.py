import logging
import requests  # Added for URL validation
import html
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from database_manager import get_user_credits, deduct_credit, get_user_profile, register_user_if_not_exists, is_user_subscribed, set_subscription_pending, add_xp
from learning_manager import get_user_learning, add_experience, complete_lesson
from ai_handler import get_ai_response
from nowpayments_handler import create_payment_invoice
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
MAIN_MENU = [
    [KeyboardButton("🚀 Mi Ruta de Aprendizaje"), KeyboardButton("🧪 Laboratorios Prácticos")],
    [KeyboardButton("🛒 Tienda / Recargas"), KeyboardButton("⚙️ Mi Cuenta")],
    [KeyboardButton("👥 Comunidad"), KeyboardButton("🛠️ Tools")]
]

TOOLS_MENU = [
    [KeyboardButton("🌐 Web Tools"), KeyboardButton("📄 PDF Tools")],
    [KeyboardButton("📦 Repositorios"), KeyboardButton("📜 Scripts")],
    [KeyboardButton("📱 Termux"), KeyboardButton("🔙 Volver al Menú Principal")]
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
        # No cleaning here
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        username = update.effective_user.username
        await register_user_if_not_exists(user_id, first_name=first_name, last_name=last_name, username=username)
        
        welcome_msg = (
            f"¡Bienvenido, <b>{html.escape(first_name or 'Hacker')}</b>! 🕵️‍♂️\n\n"
            "Soy tu mentor en <b>Kali Linux</b>. Estás a punto de empezar un viaje para dominar las herramientas de los profesionales.\n\n"
            "¿Listo para desbloquear tu potencial? Elige tu camino:"
        )
        # Welcome Image
        try:
            with open('assets/welcome.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption=welcome_msg, reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending welcome image: {e}")
            # Fallback to text only
            await send_menu(update, welcome_msg, MAIN_MENU)
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
        # No cleaning here (Generic back)
        await send_menu(update, "Regresando al cuartel general...", MAIN_MENU)
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

    # 1. Ruta de Aprendizaje
    if text == "🚀 Mi Ruta de Aprendizaje":
        await clean_trigger_message(update) # KEEP CLEANING HERE
        from learning_content import SECTIONS, MODULES
        from database_manager import get_user_completed_modules
        
        completed = await get_user_completed_modules(user_id)
        
        # Find next uncompleted module for "Continue" button
        next_module_id = 1
        for i in range(1, 101):
            if i not in completed:
                next_module_id = i
                break
        
        msg = (
            "<b>🗺️ MAPA DE RUTA HACKER</b>\n\n"
            "Has entrado en la zona de entrenamiento táctico. Aquí transformaremos tu curiosidad en una arma cibernética letal.\n\n"
            f"📊 <b>Tu Progreso Actual:</b> {len(completed)}/100 Módulos Completados\n"
            "🎯 <b>Objetivo:</b> Dominar las 10 fases del Hacking Ético.\n\n"
            "<i>Selecciona tu nivel para desplegar las misiones:</i>"
        )
        
        keyboard = []
        
        # Continue Button
        keyboard.append([KeyboardButton(f"▶️ Continuar: Módulo {next_module_id}")])
        
        row = []
        for sec_id, data in SECTIONS.items():
            # Check access
            is_free = data['free']
            status = "🔓" if is_free else "🔒"
            
            # If user is subscribed, everything is unlocked
            if await is_user_subscribed(user_id):
                status = "🔓"
            
            # Calculate progress in section
            sec_mods = [k for k in MODULES if MODULES[k]['section'] == sec_id]
            sec_completed = len([m for m in sec_mods if m in completed])
            total_sec = len(sec_mods)
            
            if sec_completed == total_sec:
                status = "✅"
            
            btn_text = f"{status} {data['title']} ({sec_completed}/{total_sec})"
            row.append(KeyboardButton(btn_text))
            if len(row) == 1: # One section per row
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 Volver al Menú Principal")])
        
        # Image for Learning Path
        try:
            with open('assets/learning.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption=msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending learning path image: {e}")
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        return

    # Handle "Continue" Button
    if text.startswith("▶️ Continuar:"):
        # Logic handled in next block, but let's clean message here too if possible, 
        # but the next block needs 'text' to be preserved. 
        # clean_trigger_message will delete the message object, but 'text' variable persists.
        await clean_trigger_message(update)
        try:
            mod_id = int(text.split("Módulo ")[1])
            # Trigger the view module logic
            text = f"📑 Ver Mod {mod_id}"
            # Fallthrough to next handler
        except:
            pass

    # Handle Section Selection
    from learning_content import SECTIONS, MODULES
    selected_section = None
    for sec_id, data in SECTIONS.items():
        if data['title'] in text: # Simple substring match might be risky if titles overlap, but titles are distinct enough
            selected_section = sec_id
            break
            
    if selected_section:
        await clean_trigger_message(update)
        # Check Access
        is_free = SECTIONS[selected_section]['free']
        if not is_free and not await is_user_subscribed(user_id):
            # Generate Invoice for immediate action
            from nowpayments_handler import create_payment_invoice
            from database_manager import set_subscription_pending
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            amount = 10.0
            invoice = create_payment_invoice(amount, user_id)
            
            msg = (
                "⛔ <b>ACCESO CLASIFICADO: NIVEL 5</b>\n\n"
                "Has llegado al límite de la zona gratuita, Hacker. Lo que sigue es conocimiento de élite que separa a los script kiddies de los profesionales.\n\n"
                "🔓 <b>Al desbloquear la Zona Premium obtienes:</b>\n"
                "• 📚 Acceso a los 100 Módulos (De Cero a Experto)\n"
                "• 🎓 Certificados Oficiales por cada logro\n"
                "• 🧪 Laboratorios de Hacking Real\n"
                "• 🤖 IA Ilimitada sin restricciones\n\n"
                "👇 <b>No te detengas ahora. Tu futuro te espera.</b>"
            )
            
            keyboard = []
            if invoice and invoice.get('invoice_url') and is_url_valid(invoice['invoice_url']):
                await set_subscription_pending(user_id, invoice.get('invoice_id'))
                keyboard = [[InlineKeyboardButton("🚀 Desbloquear Acceso Total ($10)", url=invoice['invoice_url'])]]
            else:
                keyboard = []  # No valid URL, omit button            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                parse_mode=ParseMode.HTML
            )
            return
            
        from database_manager import get_user_completed_modules
        completed = await get_user_completed_modules(user_id)
            
        # Show Modules for this Section
        msg = f"<b>{SECTIONS[selected_section]['title']}</b>\n\nSelecciona un módulo:\n"
        keyboard = []
        
        # Filter modules for this section
        section_modules = [m for k, m in MODULES.items() if m['section'] == selected_section]
        
        for mod in section_modules:
            mod_id = [k for k, v in MODULES.items() if v == mod][0]
            
            # Status Logic
            if mod_id in completed:
                status = "✅"
            else:
                status = "🔒" # Default locked visual
                # Check if previous module is completed (or if it's the first one)
                if mod_id == 1 or (mod_id - 1) in completed:
                    status = "🔓" # Unlocked/Next
            
            # Full Title (Single Column)
            title = mod['title']
            # Truncate slightly if extremely long to fit Telegram limit (approx 40-50 chars is safe)
            if len(title) > 40:
                title = title[:37] + "..."
                
            btn_text = f"{status} {mod_id}. {title}"
            
            # Single column append
            keyboard.append([KeyboardButton(f"📑 {mod_id}: {title}")])
                
        keyboard.append([KeyboardButton("🚀 Mi Ruta de Aprendizaje")]) # Back to sections
        
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        return

    # Updated Handler for Module View
    # Matches various button formats:
    # "📑 X: Title"
    # "📑 Ver Mod X" (legacy)
    # "▶️ Continuar: Módulo X"
    # "▶️ Siguiente: X. Title"
    # "⬅️ Repasar: X. Title"
    
    if (text.startswith("📑") or 
        text.startswith("▶️ Continuar") or 
        text.startswith("▶️ Siguiente") or 
        text.startswith("⬅️ Repasar")):
        
        await clean_trigger_message(update)
        
        try:
            # Extract ID. 
            # We look for the first number in the string.
            # Examples: "📑 5: Redes...", "▶️ Siguiente: 6. Tu Primer..."
            import re
            match = re.search(r'\d+', text)
            if not match:
                # If no number found, maybe it's just an icon click without number (unlikely with current buttons)
                return
            
            mod_id = int(match.group())
            
            if mod_id not in MODULES:
                return
                
            module = MODULES[mod_id]
            section = SECTIONS[module['section']]
            
            # Verify Access
            if not section['free'] and not await is_user_subscribed(user_id):
                await update.message.reply_text("🔒 Requiere Suscripción Premium.", parse_mode=ParseMode.HTML)
                return
                
            # Verify Sequential Access (Gamification)
            from database_manager import get_user_completed_modules
            completed = await get_user_completed_modules(user_id)
            
            # Find the first incomplete module (The user's real current step)
            first_incomplete = 1
            for i in range(1, 101):
                if i not in completed:
                    first_incomplete = i
                    break
            
            # If trying to access a future module (skipping steps)
            if mod_id > first_incomplete and mod_id not in completed:
                 target_title = MODULES[first_incomplete]['title']
                 if len(target_title) > 25: target_title = target_title[:22] + "..."
                 
                 msg = (
                     "🔒 <b>ACCESO DENEGADO: MÓDULO BLOQUEADO</b>\n\n"
                     f"🚫 Estás intentando saltar al <b>Módulo {mod_id}</b>, pero tu entrenamiento debe ser secuencial.\n\n"
                     f"📍 <b>Tu posición actual:</b> Módulo {first_incomplete - 1} (Completado)\n"
                     f"🎯 <b>Siguiente objetivo:</b> Debes completar el <b>Módulo {first_incomplete}</b> para avanzar.\n\n"
                     "<i>Un verdadero hacker no deja brechas en su conocimiento.</i>"
                 )
                 
                 # Redirection Button
                 kb = [[KeyboardButton(f"▶️ Siguiente: {first_incomplete}. {target_title}")]]
                 kb.append([KeyboardButton("🚀 Mi Ruta de Aprendizaje")])
                 
                 await update.message.reply_text(
                     msg, 
                     reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                     parse_mode=ParseMode.HTML
                 )
                 return
                
            # 1. Send local image (Visual Header)
            try:
                with open(module['img'], 'rb') as img_file:
                    await update.message.reply_photo(
                        photo=img_file,
                        caption=f"<b>MÓDULO {mod_id}: {module['title'].upper()}</b>",
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending module image {module['img']}: {e}")

            # 2. Send Text with Description (No Link Preview, Button Only)
            # We remove the explicit link from text to avoid clutter and broken Instant View on Desktop.
            # The user will use the Inline Button to open the lesson reliably.
            
            msg = (
                f"{module['desc']}\n\n"
                f"👇 <b>Presiona el botón para comenzar:</b>"
            )
            
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            # Button opens the link in the default browser/webview, avoiding Desktop bugs
            kb = []
            if is_url_valid(module['link']):
                kb = [[InlineKeyboardButton("📖 Abrir Lección Completa", url=module['link'])]]
            else:
                msg += "\n\n⚠️ <b>Nota:</b> El contenido está en mantenimiento temporalmente."
            
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(kb) if kb else None,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True # FIX: Disable broken preview on Desktop
            )
            
            # Check if already completed to adjust Action Button
            is_completed = mod_id in completed
            
            reply_kb = []
            
            # --- NEXT / COMPLETE BUTTON ---
            if is_completed:
                # If completed, show "Next Module" instead of "Complete"
                msg_status = "✅ <b>Módulo Completado</b>\nPuedes repasar el contenido o avanzar."
                
                # Find next module title for the button
                next_mod_id = mod_id + 1
                if next_mod_id in MODULES:
                     next_title = MODULES[next_mod_id]['title']
                     if len(next_title) > 25: next_title = next_title[:22] + "..."
                     reply_kb.append([KeyboardButton(f"▶️ Siguiente: {next_mod_id}. {next_title}")])
                else:
                     reply_kb.append([KeyboardButton("🚀 Mi Ruta de Aprendizaje")])
            else:
                # If not completed, show "Complete" button
                msg_status = "⚠️ <b>Misión en curso...</b>\n\nCuando hayas asimilado la información, confirma para recibir tu recompensa (XP + Progreso)."
                reply_kb.append([KeyboardButton(f"✅ Completar Módulo {mod_id}")])

            # --- PREVIOUS BUTTON (From Module 2 onwards) ---
            if mod_id > 1:
                prev_mod_id = mod_id - 1
                if prev_mod_id in MODULES:
                    prev_title = MODULES[prev_mod_id]['title']
                    if len(prev_title) > 25: prev_title = prev_title[:22] + "..."
                    reply_kb.append([KeyboardButton(f"⬅️ Repasar: {prev_mod_id}. {prev_title}")])

            # --- NAVIGATION & MAP ---
            # Add Section button if completed, otherwise just Map
            if is_completed:
                reply_kb.append([KeyboardButton(f"📂 {SECTIONS[module['section']]['title']}")])
            
            reply_kb.append([KeyboardButton("🚀 Mi Ruta de Aprendizaje")])
            
            await update.message.reply_text(
                msg_status,
                reply_markup=ReplyKeyboardMarkup(reply_kb, resize_keyboard=True),
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error showing module: {e}")
        return

    if text.startswith("✅ Completar Módulo"):
        await clean_trigger_message(update)
        try:
            mod_id = int(text.split()[-1])
            from database_manager import mark_module_completed, get_user_profile
            from certificate_generator import generate_certificate
            from learning_content import MODULES, SECTIONS
            import os
            
            # Mark in DB
            success = await mark_module_completed(user_id, mod_id)
            if success:
                await update.message.reply_text("🎉 ¡Felicidades! Has completado el módulo. Generando tu certificado...", parse_mode=ParseMode.HTML)
                
                # Generate Cert
                user_name = update.effective_user.first_name
                if update.effective_user.last_name:
                    user_name += f" {update.effective_user.last_name}"
                
                module_title = MODULES[mod_id]['title']
                cert_path = generate_certificate(user_name, user_id, module_title)
                
                if cert_path and os.path.exists(cert_path):
                    await update.message.reply_photo(photo=open(cert_path, 'rb'), caption=f"🎓 <b>Certificado de Finalización</b>\n\nHas dominado: {module_title}", parse_mode=ParseMode.HTML)
                    try:
                        os.remove(cert_path)
                    except:
                        pass
                else:
                    await update.message.reply_text("Hubo un error generando la imagen del certificado, pero tu progreso ha sido guardado.", parse_mode=ParseMode.HTML)
                
                # --- SMART NAVIGATION (SINGLE COLUMN WITH TITLES) ---
                next_mod_id = mod_id + 1
                prev_mod_id = mod_id - 1
                current_section_id = MODULES[mod_id]['section']
                current_section_title = SECTIONS[current_section_id]['title']
                
                keyboard = []
                
                # Next Module Button (Priority)
                if next_mod_id in MODULES:
                    next_title = MODULES[next_mod_id]['title']
                    if len(next_title) > 30: next_title = next_title[:27] + "..."
                    keyboard.append([KeyboardButton(f"▶️ Siguiente: {next_mod_id}. {next_title}")])
                
                # Previous Module Button
                if prev_mod_id in MODULES:
                    prev_title = MODULES[prev_mod_id]['title']
                    if len(prev_title) > 30: prev_title = prev_title[:27] + "..."
                    keyboard.append([KeyboardButton(f"⬅️ Repasar: {prev_mod_id}. {prev_title}")])
                
                # Back to Section
                keyboard.append([KeyboardButton(f"📂 {current_section_title}")])
                
                # Back to Map
                keyboard.append([KeyboardButton("🚀 Mi Ruta de Aprendizaje")])
                
                await update.message.reply_text(
                    "<b>¿Cuál es tu siguiente paso, Hacker?</b> 💀\n\nContinúa tu entrenamiento o repasa lo aprendido.",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
                    parse_mode=ParseMode.HTML
                )
                
            else:
                await update.message.reply_text("Error al guardar el progreso. Intenta de nuevo.", parse_mode=ParseMode.HTML)
                
        except Exception as e:
            logger.exception(f"Error completing module: {e}")
        return

    # 2. Laboratorios Prácticos
    if text == "🧪 Laboratorios Prácticos":
        await clean_trigger_message(update)
        # Check Premium Access FIRST
        if not await is_user_subscribed(user_id):
            from nowpayments_handler import create_payment_invoice
            from database_manager import set_subscription_pending
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            amount = 10.0
            invoice = create_payment_invoice(amount, user_id)
            
            msg = (
                "⛔ <b>ACCESO CLASIFICADO: LABORATORIOS DE ÉLITE</b>\n\n"
                "Has intentado acceder al Simulador de Ciberseguridad Avanzado. Esta zona está restringida solo para personal autorizado (Premium).\n\n"
                "🔓 <b>Al suscribirte obtendrás acceso a:</b>\n"
                "• 🖥️ <b>Simulador de Terminal Realista:</b> Practica sin riesgos.\n"
                "• 🚩 <b>100+ Escenarios CTF:</b> Redes, Web, Cripto y Forense.\n"
                "• 🛠️ <b>Herramientas Pro:</b> Nmap, SQLMap, Hashcat, Metasploit.\n"
                "• 🏆 <b>Ranking Global:</b> Compite contra otros hackers.\n\n"
                "👇 <b>Invierte en tu futuro hoy mismo:</b>"
            )
            
            kb = []
            if invoice and invoice.get('invoice_url') and is_url_valid(invoice['invoice_url']):
                await set_subscription_pending(user_id, invoice.get('invoice_id'))
                kb = [[InlineKeyboardButton("🚀 Desbloquear Laboratorios ($10)", url=invoice['invoice_url'])]]
            else:
                kb = []  # Invalid or missing URL            
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            return

        # If Subscribed, show the full menu
        from labs_content import LAB_CATEGORIES
        msg = (
            "<b>🧪 LABORATORIOS DE HACKING</b>\n\n"
            "Bienvenido al simulador, Agente. Aquí pondrás a prueba tu teoría en entornos controlados.\n"
            "Cada laboratorio es un desafío único diseñado para romper tus límites.\n\n"
            "<i>Selecciona una categoría para comenzar tu entrenamiento:</i>"
        )
        
        keyboard = []
        row = []
        for key, name in LAB_CATEGORIES.items():
            row.append(KeyboardButton(name))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 Volver al Menú Principal")])
        
        # Image for Labs
        try:
            with open('assets/labs.jpg', 'rb') as img:
                await update.message.reply_photo(img, caption=msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending labs image: {e}")
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        return

    # Handle Lab Category Selection
    from labs_content import LAB_CATEGORIES, LABS
    selected_cat = None
    
    # Clean text if it comes from "Volver a" button
    clean_text = text.replace("📂 Volver a ", "")
    
    for key, name in LAB_CATEGORIES.items():
        if name == clean_text:
            selected_cat = key
            break
            
    if selected_cat:
        # Show Labs in this Category
        from database_manager import get_user_completed_labs
        completed_labs = await get_user_completed_labs(user_id)
        
        msg = f"<b>{clean_text}</b>\n\nSelecciona un escenario:"
        keyboard = []
        
        cat_labs = [l for k, l in LABS.items() if l['cat'] == selected_cat]
        
        for lab in cat_labs:
            lab_id = [k for k, v in LABS.items() if v == lab][0]
            
            # Status
            status = "🔒"
            if not lab['premium']: status = "🆓" # Free labs
            if lab_id in completed_labs: status = "✅"
            
            # Check Premium Access for visual lock
            if lab['premium'] and not await is_user_subscribed(user_id):
                status = "🔒"
            
            # Single Column Layout for better readability
            keyboard.append([KeyboardButton(f"🔬 Lab {lab_id}: {lab['title']} {status}")])
            
        keyboard.append([KeyboardButton("🧪 Laboratorios Prácticos")])
        
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode=ParseMode.HTML)
        return

    # Handle Lab Selection
    if text.startswith("🔬 Lab"):
        try:
            import re
            match = re.search(r'\d+', text)
            if not match: return
            lab_id = int(match.group())
            
            if lab_id not in LABS: return
            
            lab = LABS[lab_id]
            
            # Check Premium
            if lab['premium'] and not await is_user_subscribed(user_id):
                # Upsell logic (omitted for brevity, same as before)
                from nowpayments_handler import create_payment_invoice
                from database_manager import set_subscription_pending
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                
                amount = 10.0
                invoice = create_payment_invoice(amount, user_id)
                
                msg = (
                    "⛔ <b>ACCESO DENEGADO: LABORATORIO PREMIUM</b>\n\n"
                    "Este escenario requiere herramientas avanzadas solo disponibles para suscriptores.\n\n"
                    "🔓 <b>Desbloquea el Simulador Completo:</b>\n"
                    "• +20 Escenarios Reales (Redes, Web, Cripto)\n"
                    "• Herramientas: Nmap, SQLMap, Hashcat (Simuladas)\n"
                    "• XP Doble y Rangos Exclusivos\n\n"
                    "👇 <b>Accede ahora:</b>"
                )
                
                kb = []
                if invoice and invoice.get('invoice_url') and is_url_valid(invoice['invoice_url']):
                    await set_subscription_pending(user_id, invoice.get('invoice_id'))
                    kb = [[InlineKeyboardButton("🚀 Desbloquear Laboratorios ($10)", url=invoice['invoice_url'])]]
                else:
                    kb = [] # Invalid URL
                
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode=ParseMode.HTML)
                return
            
            # Check if Completed
            from database_manager import get_user_completed_labs
            completed_labs = await get_user_completed_labs(user_id)
            is_completed = lab_id in completed_labs
            
            if is_completed:
                msg = (
                    f"✅ <b>MISIÓN COMPLETADA: {lab['title'].upper()}</b>\n\n"
                    f"Ya has dominado este escenario, Hacker.\n\n"
                    f"🚩 <b>Flag Obtenida:</b> <code>{lab['flag']}</code>\n"
                    f"💰 <b>XP Ganada:</b> {lab['xp']}\n\n"
                    f"👇 <b>Opciones:</b> Puedes volver a practicar o buscar un nuevo reto."
                )
            else:
                msg = (
                    f"🕵️‍♂️ <b>MISIÓN: {lab['title'].upper()}</b>\n\n"
                    f"{lab['mission']}\n\n"
                    f"💰 <b>Recompensa:</b> {lab['xp']} XP\n"
                    f"👇 <b>Instrucciones:</b> Pulsa el botón para iniciar la terminal y ejecutar el comando de reconocimiento."
                )
            
            # Action Buttons
            kb = [
                [KeyboardButton(f"🖥️ Ejecutar: {lab['command']}")],
                [KeyboardButton("💡 Pista"), KeyboardButton(f"📂 Volver a {LAB_CATEGORIES[lab['cat']]}")],
                [KeyboardButton("🧪 Laboratorios Prácticos")]
            ]
            
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error showing lab: {e}")
        return

    # Handle Lab Execution (Simulation)
    if text.startswith("🖥️ Ejecutar:"):
        try:
            command = text.replace("🖥️ Ejecutar: ", "")
            # Find which lab has this command (Simple lookup, assumes unique commands or context)
            # Better: We need context. But for now, let's search LABS.
            current_lab_id = None
            for lid, l in LABS.items():
                if l['command'] == command:
                    current_lab_id = lid
                    break
            
            if not current_lab_id: return
            
            lab = LABS[current_lab_id]
            
            # Show Terminal Output
            terminal_msg = (
                f"💻 <b>TERMINAL KALI LINUX</b>\n"
                f"<pre language='bash'>root@kali:~# {lab['command']}\n"
                f"{lab['output']}</pre>\n\n"
                f"❓ <b>DESAFÍO:</b>\n{lab['question']}\n\n"
                f"✍️ <b>Escribe tu respuesta abajo (Flag):</b>"
            )
            
            await update.message.reply_text(terminal_msg, parse_mode=ParseMode.HTML)
            
            # Set context for answer checking (We can't easily set context in this stateless flow without DB or memory)
            # Workaround: We will check answers in the generic text handler by matching against ALL active labs flags.
            # Or better: The user just types the answer. We check if text matches ANY lab flag.
            
        except Exception as e:
            logger.error(f"Error executing lab: {e}")
        return

    if text == "💡 Pista":
        await update.message.reply_text(
            "🔍 <b>PISTA TÁCTICA</b>\n\n"
            "1. Lee cada línea del output de la terminal.\n"
            "2. Busca palabras clave como 'PORT', 'VERSION', 'File', 'User'.\n"
            "3. La flag suele ser un dato concreto (número, nombre, hash).\n\n"
            "<i>Si te atascas, prueba a ejecutar el comando de nuevo.</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # Check for Lab Answers (Flags)
    # This runs for any text that didn't match a command
    # We iterate through all labs to see if the text matches a flag
    # To avoid false positives, we only check if the text looks like a flag or answer (short)
    if len(text) < 50:
        for lid, l in LABS.items():
            if text.strip().lower() == l['flag'].lower():
                # Correct Answer!
                from database_manager import mark_lab_completed, add_xp, get_user_completed_labs
                
                # Check if already completed
                completed = await get_user_completed_labs(user_id)
                if lid in completed:
                    await update.message.reply_text(f"✅ <b>¡Correcto!</b>\nYa habías completado este laboratorio.", parse_mode=ParseMode.HTML)
                    return
                
                # Mark complete
                await mark_lab_completed(user_id, lid)
                await add_xp(user_id, l['xp'])
                
                await update.message.reply_text(
                    f"🎉 <b>¡MISIÓN CUMPLIDA!</b>\n\n"
                    f"✅ Respuesta Correcta: <b>{l['flag']}</b>\n"
                    f"💰 Has ganado <b>{l['xp']} XP</b>.\n\n"
                    f"Sigue así, Hacker.",
                    parse_mode=ParseMode.HTML
                )
                
                # Show navigation
                kb = [[KeyboardButton(f"📂 Volver a {LAB_CATEGORIES[l['cat']]}")] , [KeyboardButton("🧪 Laboratorios Prácticos")]]
                await update.message.reply_text("¿Cuál es tu siguiente objetivo?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                return

    # 3. Desafíos
    # 3. Desafíos (ELIMINADO)
    # if text == "🏆 Desafíos & CTFs":
    #    await send_menu(update, "¡Demuestra tu valía en la arena! ⚔️", CHALLENGES_MENU)
    #    return

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
        
        if chart_path and os.path.exists(chart_path):
            await update.message.reply_photo(photo=open(chart_path, 'rb'), caption=caption, parse_mode=ParseMode.HTML)
            try:
                os.remove(chart_path)
            except:
                pass
        else:
            await update.message.reply_text(caption, parse_mode=ParseMode.HTML)
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
                    
                    # Remove the tag from text
                    clean_response = clean_response.replace(script_match.group(0), "")


            # Find all [[BUTTON: Label | URL]] patterns
            # Regex handles optional whitespace and potential markdown/HTML noise around the tag
            matches = re.findall(r"\[\[BUTTON:\s*(.*?)\s*\|\s*(.*?)\]\]", respuesta)
            
            if matches:
                for label, url in matches:
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
                
                # Remove the button tags from the visible text
                clean_response = re.sub(r"\[\[BUTTON:.*?\]\]", "", respuesta).strip()

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
