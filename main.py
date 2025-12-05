from fastapi import FastAPI, Request, HTTPException, Response
import socket
from contextlib import asynccontextmanager
import uvicorn
import logging
import os
import json

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from bot_logic import handle_message, handle_callback
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET, DELETE_WEBHOOK_ON_POLLING, SKIP_ENV_VALIDATION, FALLBACK_AI_TEXT
from config import validate_config

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)
ENV = os.getenv('ENV', 'production').lower()
IN_PROD = ENV == 'production'

# Optionally allow webhook to persist across shutdowns to avoid losing webhook during platform restarts
PERSIST_WEBHOOK_ON_SHUTDOWN = os.getenv('PERSIST_WEBHOOK_ON_SHUTDOWN', '0').lower() in ['1', 'true', 'yes']
ENABLE_DEBUG_ENDPOINTS = os.getenv('ENABLE_DEBUG_ENDPOINTS', '0').lower() in ['1', 'true', 'yes']

validate_config()
if TELEGRAM_BOT_TOKEN is None:
    raise EnvironmentError('TELEGRAM_BOT_TOKEN must be set in production')
# Build Application with increased timeouts
telegram_app = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .read_timeout(120)
    .write_timeout(120)
    .connect_timeout(120)
    .pool_timeout(120)
    .build()
)
telegram_app.add_handler(CommandHandler('start', handle_message))
telegram_app.add_handler(CommandHandler('saldo', handle_message))
telegram_app.add_handler(CommandHandler('comprar', handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

TELEGRAM_STARTED = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and start Telegram app inside lifespan
    try:
        await telegram_app.initialize()
        await telegram_app.start()
        global TELEGRAM_STARTED
        TELEGRAM_STARTED = True
        logger.info('Telegram application started via lifespan.')
        if TELEGRAM_WEBHOOK_URL:
            if TELEGRAM_WEBHOOK_URL.rstrip('/').endswith('onrender.com'):
                logger.warning('TELEGRAM_WEBHOOK_URL appears to be the root domain. Consider using the full webhook path: https://<your-domain>/webhook/telegram')
            if '/webhook' not in TELEGRAM_WEBHOOK_URL:
                logger.warning('TELEGRAM_WEBHOOK_URL does not include a webhook path. POSTs to the root path may return 405; consider using /webhook/telegram')
            try:
                logger.info('Setting Telegram webhook to %s', TELEGRAM_WEBHOOK_URL)
                if TELEGRAM_WEBHOOK_SECRET:
                    await telegram_app.bot.set_webhook(TELEGRAM_WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET)
                else:
                    await telegram_app.bot.set_webhook(TELEGRAM_WEBHOOK_URL)
                logger.info('Webhook set successfully')
            except Exception as e:
                logger.exception('Failed to set webhook: %s', e)
        else:
            # In production we expect a webhook URL; if not set, log strongly but don't crash if validation was skipped.
            if not SKIP_ENV_VALIDATION:
                logger.error('TELEGRAM_WEBHOOK_URL is not set — running in webhook mode without a webhook may cause missed updates')
        if IN_PROD and TELEGRAM_WEBHOOK_URL and not TELEGRAM_WEBHOOK_URL.startswith('https://'):
            logger.error('TELEGRAM_WEBHOOK_URL does not use HTTPS; this is insecure for production')
    except Exception:
        # Keep server running even if Telegram initialization fails
        logger.exception('Error initializing Telegram app; continuing to serve HTTP endpoints')
    # start heartbeat
    try:
        import asyncio
        async def _heartbeat():
            import resource
            while True:
                try:
                    usage = resource.getrusage(resource.RUSAGE_SELF)
                    rss = usage.ru_maxrss
                    utime = usage.ru_utime
                    stime = usage.ru_stime
                    logger.info('Heartbeat: service alive (pid=%s) rss=%sKB utime=%s stime=%s', os.getpid(), rss, utime, stime)
                except Exception:
                    logger.info('Heartbeat: service alive (pid=%s)', os.getpid())
                await asyncio.sleep(60)
        hb = asyncio.create_task(_heartbeat())
        app.state.heartbeat_task = hb
        
        # Start subscription check task
        async def _subscription_check_loop():
            from database_manager import get_expiring_users, expire_overdue_subscriptions
            while True:
                try:
                    logger.info("Running daily subscription check...")
                    # 1. Expire overdue
                    expired_count = await expire_overdue_subscriptions()
                    if expired_count > 0:
                        logger.info(f"Expired {expired_count} subscriptions.")
                    
                    # 2. Notify expiring in 3 days
                    expiring_users = await get_expiring_users(days=3)
                    for user in expiring_users:
                        uid = user['user_id']
                        try:
                            await telegram_app.bot.send_message(
                                chat_id=uid,
                                text="⚠️ <b>Tu suscripción Premium vence en 3 días.</b>\n\nNo pierdas acceso a tus herramientas exclusivas. Renueva ahora con /suscribirse.",
                                parse_mode='HTML'
                            )
                            logger.info(f"Sent expiry reminder to {uid}")
                        except Exception as e:
                            logger.warning(f"Failed to send reminder to {uid}: {e}")
                            
                    logger.info("Subscription check complete.")
                except Exception as e:
                    logger.exception(f"Error in subscription check loop: {e}")
                
                # Wait 24 hours
                await asyncio.sleep(24 * 3600)
                
        sub_task = asyncio.create_task(_subscription_check_loop())
        app.state.sub_task = sub_task
        
    except Exception:
        logger.debug('Could not create background tasks')

    # yield control to FastAPI loop
    try:
        yield
    finally:
        try:
            if TELEGRAM_WEBHOOK_URL and not PERSIST_WEBHOOK_ON_SHUTDOWN:
                try:
                    await telegram_app.bot.delete_webhook()
                    logger.info('Deleted Telegram webhook')
                except Exception as e:
                    logger.exception('Failed to delete Telegram webhook: %s', e)
            await telegram_app.stop()
            await telegram_app.shutdown()
            TELEGRAM_STARTED = False
            logger.info('Telegram application stopped via lifespan.')
        except Exception:
            logger.exception('Error while stopping Telegram application')
        # Cancel tasks
        try:
            hb = getattr(app.state, 'heartbeat_task', None)
            if hb:
                hb.cancel()
            st = getattr(app.state, 'sub_task', None)
            if st:
                st.cancel()
        except Exception:
            logger.exception('Error while attempting to cancel background tasks')

    # Attempt to set signal handlers for additional logging
    try:
        import signal
        def _log_signal(sig, frame):
            logger.info('Process received signal %s; exiting', sig)
        signal.signal(signal.SIGTERM, _log_signal)
        signal.signal(signal.SIGINT, _log_signal)
    except Exception:
        logger.debug('Could not set signal handlers for logging')


app = FastAPI(lifespan=lifespan)


def debug_guard():
    if not ENABLE_DEBUG_ENDPOINTS:
        raise HTTPException(status_code=403, detail='Debug endpoints are disabled in this environment')


@app.post('/webhook/telegram')
async def telegram_webhook(request: Request):
    body = await request.json()
    telegram_secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token') or request.headers.get('x-telegram-bot-api-secret-token')
    from config import TELEGRAM_WEBHOOK_SECRET
    if TELEGRAM_WEBHOOK_SECRET and (telegram_secret_header != TELEGRAM_WEBHOOK_SECRET):
        logger.warning('Rejected webhook request with invalid secret header')
        raise HTTPException(status_code=401, detail='Invalid webhook secret')
    try:
        update = Update.de_json(body, telegram_app.bot)
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid Update payload')
    logger.debug('Received webhook update: %s', body)
    await telegram_app.update_queue.put(update)
    return {'status': 'ok'}


@app.post('/webhook/nowpayments')
async def nowpayments_webhook(request: Request):
    signature = request.headers.get('x-nowpayments-sig', '')
    body = await request.body()
    from nowpayments_handler import process_nowpayments_webhook
    result = await process_nowpayments_webhook(body, signature)
    if result['status'] != 200:
        raise HTTPException(status_code=result['status'], detail=result['message'])
    return result


@app.get('/')
async def root():
    return {'status': 'ok', 'service': 'kali-tutor-bot'}


@app.head('/')
async def root_head() -> Response:
    return Response(status_code=200)


@app.post('/debug/register')
async def debug_register(request: Request):
    debug_guard()
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id is required')
    try:
        from database_manager import register_user_if_not_exists
        created = await register_user_if_not_exists(int(user_id), first_name=first_name, last_name=last_name, username=username)
        return {'status': 'ok', 'created': created}
    except Exception as e:
        logger.exception('debug_register error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/debug/register-raw')
async def debug_register_raw(request: Request):
    debug_guard()
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id is required')
    try:
        from database_manager import supabase
        payload = {'user_id': int(user_id)}
        if 'first_name' in data and data['first_name'] is not None:
            payload['first_name'] = data['first_name']
        if 'last_name' in data and data['last_name'] is not None:
            payload['last_name'] = data['last_name']
        if 'username' in data and data['username'] is not None:
            payload['username'] = data['username']
        res = supabase.table('usuarios').upsert(payload).execute()
        result = {'data': getattr(res, 'data', None), 'error': getattr(res, 'error', None), 'status_code': getattr(res, 'status_code', None)}
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_register_raw error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/debug/register-rpc')
async def debug_register_rpc(request: Request):
    debug_guard()
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    initial_balance = data.get('initial_balance', 0)
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id is required')
    try:
        from database_manager import supabase
        params = {'uid': int(user_id), 'first_name': first_name, 'last_name': last_name, 'username': username, 'initial_balance': int(initial_balance)}
        res = supabase.rpc('add_or_update_user', params).execute()
        result = {'data': getattr(res, 'data', None), 'error': getattr(res, 'error', None), 'status_code': getattr(res, 'status_code', None)}
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_register_rpc error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/debug/env')
async def debug_env():
    debug_guard()
    import os
    checks = {
        'TELEGRAM_BOT_TOKEN_present': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
        'SUPABASE_URL_present': bool(os.getenv('SUPABASE_URL')),
        'SUPABASE_ANON_KEY_present': bool(os.getenv('SUPABASE_ANON_KEY')),
        'SUPABASE_SERVICE_KEY_present': bool(os.getenv('SUPABASE_SERVICE_KEY')),
        'GROQ_API_KEY_present': bool(os.getenv('GROQ_API_KEY')),
    }
    return {'status': 'ok', 'env': checks}


@app.post('/debug/deduct')
async def debug_deduct(request: Request):
    debug_guard()
    data = await request.json()
    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id is required')
    try:
        from database_manager import supabase, get_user_credits
        before = await get_user_credits(int(user_id))
        res = supabase.rpc('deduct_credit', {'uid': int(user_id)}).execute()
        after = await get_user_credits(int(user_id))
        result = {'before': before, 'raw_rpc': {'data': getattr(res, 'data', None), 'error': getattr(res, 'error', None), 'status_code': getattr(res, 'status_code', None)}, 'after': after}
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_deduct error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/debug/db-check')
async def debug_db_check():
    debug_guard()
    try:
        from database_manager import test_connection
        ok = test_connection()
        return {'status': 'ok', 'db_ok': ok}
    except Exception as e:
        logger.exception('db-check error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/status')
async def status():
    return {'telegram_started': TELEGRAM_STARTED, 'bot_service': 'kali-tutor-bot'}


@app.get('/healthz')
async def healthz():
    from database_manager import test_connection
    res = {'telegram_started': TELEGRAM_STARTED, 'db_ok': False}
    try:
        ok = test_connection()
        res['db_ok'] = bool(ok)
    except Exception as e:
        logger.exception('Health check DB error: %s', e)
    status_code = 200 if res['db_ok'] else 503
    return Response(content=json.dumps(res), status_code=status_code, media_type='application/json')


def is_port_free(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        s.close()
        return True
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        return False


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    host = '0.0.0.0'
    if not is_port_free(host, port):
        print(f'Port {port} appears to be in use. Trying higher ports up to {port+9}...')
        found = None
        for p in range(port + 1, port + 10):
            if is_port_free(host, p):
                found = p
                break
        if found is None:
            print(f'No free ports found in range {port+1} to {port+9}. Aborting.')
            exit(1)
        else:
            print(f'Using fallback port {found} instead of {port}.')
            port = found
    workers = int(os.getenv('UVICORN_WORKERS', '1'))
    logger.info('Starting uvicorn with host=%s port=%s workers=%s log_level=%s', host, port, workers, LOG_LEVEL)
    uvicorn.run('main:app', host=host, port=port, log_level=LOG_LEVEL.lower(), workers=workers)

# --- WEB APP PREMIUM IMPLEMENTATION ---
from fastapi.responses import HTMLResponse
import hmac
import hashlib
import urllib.parse
from datetime import datetime

# 1. HTML TEMPLATES
HTML_LOADER = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KaliRoot Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background-color: #000; color: #06D6A0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: monospace; }
        .loader { border: 4px solid #333; border-top: 4px solid #06D6A0; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="loader"></div>
    <script>
        const initData = window.Telegram.WebApp.initData;
        if (!initData) {
            document.body.innerHTML = "<h3 style='color:red'>Error: No InitData found. Open from Telegram.</h3>";
        } else {
            fetch('/webapp/check', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({initData: initData})
            })
            .then(response => response.json())
            .then(data => {
                if (data.html) {
                    document.open();
                    document.write(data.html);
                    document.close();
                } else {
                    document.body.innerHTML = "<h3 style='color:red'>Error loading content.</h3>";
                }
            })
            .catch(err => {
                document.body.innerHTML = "<h3 style='color:red'>Connection Error</h3>";
            });
        }
    </script>
</body>
</html>
"""

HTML_NO_PREMIUM = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Denegado</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Orbitron', sans-serif; background-color: #000; }
        .neon-text { text-shadow: 0 0 10px #8B5CF6, 0 0 20px #8B5CF6; }
    </style>
</head>
<body class="flex flex-col items-center justify-center h-screen p-4 text-center">
    <div class="mb-8">
        <!-- Placeholder Dragon/Lock Icon -->
        <svg class="w-32 h-32 text-purple-500 mx-auto animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
    </div>
    <h1 class="text-4xl font-bold text-white mb-2 neon-text">ACCESO DENEGADO</h1>
    <p class="text-gray-400 mb-8 max-w-xs">Esta zona es exclusiva para miembros <b>Elite Premium</b>. Tu suscripción no está activa.</p>
    
    <button onclick="Telegram.WebApp.openTelegramLink('https://t.me/KalyRootAiBot?start=premium'); Telegram.WebApp.close();" 
            class="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-full shadow-[0_0_15px_rgba(139,92,246,0.5)] transition-all transform hover:scale-105">
        💎 ACTIVAR PREMIUM AHORA
    </button>
</body>
</html>
"""

HTML_PREMIUM = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KaliRoot Elite Dashboard</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="//unpkg.com/alpinejs" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Rajdhani', sans-serif; background-color: #050505; color: #fff; }
        .glass { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .card-hover:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(6, 214, 160, 0.2); border-color: #06D6A0; }
        .cyan-glow { text-shadow: 0 0 10px #06D6A0; }
    </style>
</head>
<body class="p-4 pb-20">
    <!-- Header -->
    <div class="flex justify-between items-center mb-8">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-600 to-cyan-400 flex items-center justify-center font-bold text-lg">K</div>
            <div>
                <h2 class="text-xl font-bold leading-none">{user_name}</h2>
                <span class="text-xs text-cyan-400 tracking-widest uppercase">Elite Member</span>
            </div>
        </div>
        <button onclick="Telegram.WebApp.close()" class="text-gray-500 hover:text-white">✕</button>
    </div>

    <h1 class="text-3xl font-bold mb-6 cyan-glow">PREMIUM ASSETS</h1>

    <!-- Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Card 1 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300 relative overflow-hidden group">
            <div class="absolute top-0 right-0 bg-purple-600 text-xs px-2 py-1 rounded-bl-lg">HOT</div>
            <h3 class="text-xl font-bold text-white mb-1">Kali Linux Ultimate Pack</h3>
            <p class="text-gray-400 text-sm mb-4">Configuraciones, dotfiles y scripts esenciales pre-instalados.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_1" class="block w-full text-center bg-cyan-500 hover:bg-cyan-600 text-black font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>

        <!-- Card 2 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300">
            <h3 class="text-xl font-bold text-white mb-1">Termux Elite Scripts</h3>
            <p class="text-gray-400 text-sm mb-4">Automatización de ataques y setup de entorno móvil.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_2" class="block w-full text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>

        <!-- Card 3 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300">
            <h3 class="text-xl font-bold text-white mb-1">Wi-Fi Hacking Toolkit</h3>
            <p class="text-gray-400 text-sm mb-4">Wordlists optimizadas y scripts de desautenticación.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_3" class="block w-full text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>

        <!-- Card 4 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300">
            <h3 class="text-xl font-bold text-white mb-1">Web Pentest Suite</h3>
            <p class="text-gray-400 text-sm mb-4">Payloads XSS/SQLi y plantillas de reportes.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_4" class="block w-full text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>

        <!-- Card 5 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300">
            <h3 class="text-xl font-bold text-white mb-1">Anonimato & Tor Bundle</h3>
            <p class="text-gray-400 text-sm mb-4">Configuraciones de proxychains y VPNs seguras.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_5" class="block w-full text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>

        <!-- Card 6 -->
        <div class="glass p-4 rounded-xl card-hover transition-all duration-300">
            <h3 class="text-xl font-bold text-white mb-1">Exploit Database Offline</h3>
            <p class="text-gray-400 text-sm mb-4">Base de datos local de exploits buscable.</p>
            <a href="https://drive.google.com/uc?export=download&id=FILE_ID_6" class="block w-full text-center bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold py-2 rounded-lg transition-colors">
                📥 DESCARGAR .ZIP
            </a>
        </div>
    </div>
    
    <script>
        Telegram.WebApp.ready();
        Telegram.WebApp.expand();
    </script>
</body>
</html>
"""

# 2. VALIDATION LOGIC
def validate_telegram_data(init_data: str) -> dict | None:
    """Validates the initData string from Telegram Web App."""
    if not init_data: return None
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        if 'hash' not in parsed_data: return None
        
        hash_check = parsed_data.pop('hash')
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == hash_check:
            return json.loads(parsed_data.get('user', '{}'))
        return None
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return None

# 3. ROUTES
@app.get("/webapp", response_class=HTMLResponse)
async def webapp_entry():
    """Serves the loader which POSTs initData to /webapp/check for secure validation."""
    return HTML_LOADER

@app.post("/webapp/check")
async def webapp_check(request: Request):
    """Validates initData and returns the appropriate HTML (Premium vs No Premium)."""
    try:
        data = await request.json()
        init_data = data.get('initData')
        user_data = validate_telegram_data(init_data)
        
        if not user_data:
            return {"html": HTML_NO_PREMIUM} # Invalid hash
            
        user_id = user_data.get('id')
        first_name = user_data.get('first_name', 'Hacker')
        
        # Check Supabase Subscription
        from database_manager import supabase
        # We need to check if premium_until > now
        # Supabase query: select premium_until from users where user_id = ...
        res = supabase.table('usuarios').select('premium_until').eq('user_id', user_id).execute()
        
        is_premium = False
        if res.data:
            premium_until_str = res.data[0].get('premium_until')
            if premium_until_str:
                # Parse timestamp (ISO format)
                try:
                    expiry = datetime.fromisoformat(premium_until_str.replace('Z', '+00:00'))
                    if expiry > datetime.now(expiry.tzinfo):
                        is_premium = True
                except Exception:
                    pass
        
        if is_premium:
            # Inject user name into template
            return {"html": HTML_PREMIUM.format(user_name=first_name)}
        else:
            return {"html": HTML_NO_PREMIUM}
            
    except Exception as e:
        logger.exception(f"Webapp check error: {e}")
        return {"html": HTML_NO_PREMIUM}

