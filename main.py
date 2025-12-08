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


from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


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
from fastapi.responses import HTMLResponse, JSONResponse
import hmac
import hashlib
import urllib.parse
from datetime import datetime

# 1. HTML TEMPLATES - Telegram Theme Colors
# Telegram Dark Theme: bg_color=#17212b, secondary_bg=#232e3c, text=#ffffff, hint=#708499, link=#6ab2f2, button=#3390ec

HTML_LOADER = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>KaliRoot Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--tg-theme-bg-color, #17212b);
            color: var(--tg-theme-text-color, #ffffff);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .loader-container {
            text-align: center;
        }
        .spinner {
            width: 48px;
            height: 48px;
            border: 3px solid var(--tg-theme-hint-color, #708499);
            border-top-color: var(--tg-theme-button-color, #3390ec);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .status {
            color: var(--tg-theme-hint-color, #708499);
            font-size: 14px;
        }
        .error-box {
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            max-width: 320px;
        }
        .error-icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        .error-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .error-text {
            color: var(--tg-theme-hint-color, #708499);
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="loader-container" id="main">
        <div class="spinner"></div>
        <p class="status" id="status">Verificando identidad...</p>
    </div>
    <script>
        (function() {
            var tg = window.Telegram && window.Telegram.WebApp;
            var statusEl = document.getElementById('status');
            
            function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }
            
            function showError(title, msg) {
                document.getElementById('main').innerHTML = 
                    '<div class="error-box"><div class="error-icon">🔒</div><div class="error-title">' + title + '</div><div class="error-text">' + msg + '</div></div>';
            }
            
            function getInitData() {
                if (tg && tg.initData) return tg.initData;
                try {
                    var h = window.location.hash.slice(1);
                    return new URLSearchParams(h).get('tgWebAppData') || '';
                } catch(e) { return ''; }
            }
            
            function authenticate(data) {
                setStatus('Autenticando...');
                fetch('/webapp/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({initData: data})
                })
                .then(function(r) { return r.json(); })
                .then(function(res) {
                    if (res.redirect_url) {
                        setStatus('Acceso concedido');
                        window.location.href = res.redirect_url;
                    } else {
                        showError('Acceso Denegado', res.error || 'No se pudo verificar tu identidad');
                    }
                })
                .catch(function() {
                    showError('Error de Conexión', 'Verifica tu conexión a internet');
                });
            }
            
            function init() {
                if (tg) { tg.ready(); tg.expand(); }
                var data = getInitData();
                if (!data) {
                    setStatus('Esperando datos de Telegram...');
                    setTimeout(function() {
                        data = getInitData();
                        if (!data) showError('Sesión Inválida', 'Abre esta app desde el menú del bot');
                        else authenticate(data);
                    }, 1500);
                } else {
                    authenticate(data);
                }
            }
            
            if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
            else init();
        })();
    </script>
</body>
</html>"""

HTML_NO_PREMIUM = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Obtener Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #17212b);
            color: var(--tg-theme-text-color, #ffffff);
            min-height: 100vh;
            padding: 0;
        }
        .hero {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 40px 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(51, 144, 236, 0.1) 0%, transparent 50%);
            animation: pulse 4s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.1); opacity: 0.8; }
        }
        .hero-content { position: relative; z-index: 1; }
        .crown { font-size: 64px; margin-bottom: 16px; }
        .hero h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
        .hero p { color: var(--tg-theme-hint-color, #708499); font-size: 15px; }
        
        .content { padding: 24px 16px; }
        
        .price-card {
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            border: 2px solid transparent;
            transition: border-color 0.3s;
        }
        .price-card.featured {
            border-color: var(--tg-theme-button-color, #3390ec);
            position: relative;
        }
        .featured-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--tg-theme-button-color, #3390ec);
            color: #fff;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 16px;
            border-radius: 20px;
            text-transform: uppercase;
        }
        .price-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .plan-name { font-size: 18px; font-weight: 600; }
        .price { text-align: right; }
        .price-amount {
            font-size: 32px;
            font-weight: 700;
            color: var(--tg-theme-button-color, #3390ec);
        }
        .price-period {
            font-size: 13px;
            color: var(--tg-theme-hint-color, #708499);
        }
        
        .features { list-style: none; margin-bottom: 20px; }
        .features li {
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
        }
        .features li:last-child { border: none; }
        .check { color: #4ade80; font-size: 18px; }
        
        .btn {
            display: block;
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            transition: all 0.2s;
        }
        .btn-primary {
            background: var(--tg-theme-button-color, #3390ec);
            color: var(--tg-theme-button-text-color, #ffffff);
        }
        .btn-primary:active { transform: scale(0.98); opacity: 0.9; }
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .btn-loading {
            position: relative;
        }
        .btn-loading::after {
            content: '';
            width: 20px;
            height: 20px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: inline-block;
            margin-left: 8px;
            vertical-align: middle;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .status-msg {
            text-align: center;
            padding: 12px;
            border-radius: 8px;
            margin-top: 12px;
            font-size: 14px;
        }
        .status-msg.error {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
        }
        .status-msg.success {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }
        
        .guarantee {
            text-align: center;
            margin-top: 20px;
            color: var(--tg-theme-hint-color, #708499);
            font-size: 13px;
        }
        .guarantee span { color: #4ade80; }
        
        .footer-note {
            text-align: center;
            padding: 20px;
            color: var(--tg-theme-hint-color, #708499);
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="hero-content">
            <div class="crown">👑</div>
            <h1>Desbloquea el Poder Total</h1>
            <p>Conviértete en un experto en ciberseguridad</p>
        </div>
    </div>
    
    <div class="content">
        <div class="price-card featured">
            <div class="featured-badge">Más Popular</div>
            <div class="price-header">
                <span class="plan-name">Premium Mensual</span>
                <div class="price">
                    <div class="price-amount">$10</div>
                    <div class="price-period">USD / mes</div>
                </div>
            </div>
            <ul class="features">
                <li><span class="check">✓</span> 100 Módulos de Hacking Ético</li>
                <li><span class="check">✓</span> Laboratorios Prácticos Ilimitados</li>
                <li><span class="check">✓</span> 250 Créditos IA de Bienvenida</li>
                <li><span class="check">✓</span> Certificados Profesionales</li>
                <li><span class="check">✓</span> Soporte Prioritario 24/7</li>
                <li><span class="check">✓</span> Actualizaciones Exclusivas</li>
            </ul>
            <button class="btn btn-primary" id="payBtn" data-user="{user_id}">
                💎 Activar Premium Ahora
            </button>
            <div id="statusMsg"></div>
        </div>
        
        <div class="guarantee">
            <span>🔒</span> Pago seguro con criptomonedas (USDT)
        </div>
    </div>
    
    <div class="footer-note">
        Al suscribirte aceptas los términos de servicio.<br>
        Acceso inmediato después del pago confirmado.
    </div>
    
    <script>
        var tg = window.Telegram && window.Telegram.WebApp;
        if (tg) { tg.ready(); tg.expand(); }
        
        var payBtn = document.getElementById('payBtn');
        var statusMsg = document.getElementById('statusMsg');
        
        // GET USER ID DIRECTLY FROM TELEGRAM SDK (not from HTML attribute)
        var userId = null;
        if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            userId = tg.initDataUnsafe.user.id;
            console.log('Got user_id from Telegram SDK:', userId);
        }
        
        // Fallback to data attribute if SDK doesn't have it
        if (!userId) {
            var attrUserId = payBtn.getAttribute('data-user');
            if (attrUserId && attrUserId !== '{user_id}' && attrUserId !== '0') {
                userId = parseInt(attrUserId);
                console.log('Got user_id from data attribute:', userId);
            }
        }
        
        function setStatus(msg, type) {
            statusMsg.textContent = msg;
            statusMsg.className = 'status-msg ' + (type || '');
            statusMsg.style.display = msg ? 'block' : 'none';
        }
        
        function setLoading(loading) {
            payBtn.disabled = loading;
            if (loading) {
                payBtn.classList.add('btn-loading');
                payBtn.innerHTML = 'Generando enlace de pago';
            } else {
                payBtn.classList.remove('btn-loading');
                payBtn.innerHTML = '💎 Activar Premium Ahora';
            }
        }
        
        payBtn.addEventListener('click', function() {
            if (!userId) {
                setStatus('Error: No se pudo identificar tu usuario. Cierra y abre la app de nuevo.', 'error');
                return;
            }
            
            setLoading(true);
            setStatus('');
            
            fetch('/api/create-invoice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    amount: 10.0,
                    type: 'subscription'
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                setLoading(false);
                
                if (data.invoice_url) {
                    setStatus('✅ Enlace generado. Abriendo página de pago...', 'success');
                    
                    // Open payment page
                    setTimeout(function() {
                        if (tg) {
                            tg.openLink(data.invoice_url);
                        } else {
                            window.open(data.invoice_url, '_blank');
                        }
                    }, 500);
                    
                    // Change button to "check status"
                    setTimeout(function() {
                        payBtn.innerHTML = '🔄 Ya pagué - Verificar';
                        payBtn.onclick = function() {
                            window.location.reload();
                        };
                    }, 2000);
                } else {
                    setStatus('❌ ' + (data.error || 'Error al generar el enlace de pago'), 'error');
                    payBtn.innerHTML = '🔄 Reintentar';
                }
            })
            .catch(function(err) {
                setLoading(false);
                console.error('Fetch error:', err);
                setStatus('❌ Error de conexión. Intenta de nuevo.', 'error');
                payBtn.innerHTML = '🔄 Reintentar';
            });
        });
    </script>
</body>
</html>"""


HTML_PREMIUM = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>KALIROOT-AI Dashboard</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            padding-bottom: 140px;
            display: flex;
            flex-direction: column;
        }
        
        /* ===== HEADER CON LOGO ===== */
        .top-header {
            background: #0a0a0a;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            border-bottom: 1px solid rgba(51, 144, 236, 0.2);
        }
        .logo-img {
            width: 42px;
            height: 42px;
            border-radius: 10px;
            object-fit: contain;
        }
        .brand-name {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #3390ec, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* ===== USER HEADER ===== */
        .user-header {
            background: #0d0d0d;
            padding: 20px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3390ec, #00d4aa);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 700;
            color: #fff;
        }
        .user-info h2 { font-size: 17px; font-weight: 600; }
        .user-info .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #000;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 4px;
            margin-top: 4px;
        }
        
        .main-content {
            flex: 1;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding: 16px;
        }
        .stat-card {
            background: #111111;
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #3390ec;
        }
        .stat-label {
            font-size: 11px;
            color: #708499;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .section-title {
            padding: 20px 16px 12px;
            font-size: 13px;
            font-weight: 600;
            color: #708499;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .resources-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            padding: 0 16px 16px;
        }
        .resource-card {
            background: #111111;
            border-radius: 12px;
            padding: 16px;
            text-decoration: none;
            color: inherit;
            transition: transform 0.2s, box-shadow 0.2s;
            display: block;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .resource-card:active {
            transform: scale(0.98);
        }
        .resource-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }
        .resource-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .resource-desc {
            font-size: 12px;
            color: #708499;
        }
        .resource-badge {
            display: inline-block;
            background: rgba(51, 144, 236, 0.2);
            color: #3390ec;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            margin-top: 8px;
        }
        
        .action-list {
            padding: 0 16px;
        }
        .action-item {
            background: #111111;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: inherit;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .action-icon {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        .action-icon.blue { background: rgba(51, 144, 236, 0.15); }
        .action-icon.green { background: rgba(74, 222, 128, 0.15); }
        .action-icon.purple { background: rgba(168, 85, 247, 0.15); }
        .action-icon.orange { background: rgba(251, 146, 60, 0.15); }
        .action-content { flex: 1; }
        .action-title { font-size: 15px; font-weight: 500; }
        .action-subtitle { font-size: 13px; color: #708499; }
        .action-arrow { color: #708499; font-size: 18px; }
        
        /* ===== BOTTOM BAR ===== */
        .bottom-bar {
            position: fixed;
            bottom: 50px;
            left: 0;
            right: 0;
            background: #0a0a0a;
            border-top: 1px solid rgba(51, 144, 236, 0.2);
            padding: 12px 16px;
            display: flex;
            gap: 8px;
        }
        .bottom-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: transform 0.2s, opacity 0.2s;
        }
        .bottom-btn:active {
            transform: scale(0.98);
            opacity: 0.9;
        }
        .bottom-btn.primary {
            background: #3390ec;
            color: #fff;
        }
        .bottom-btn.secondary {
            background: rgba(51, 144, 236, 0.15);
            color: #3390ec;
            border: 1px solid rgba(51, 144, 236, 0.3);
        }
        
        /* ===== FOOTER ===== */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #050505;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 14px 16px;
            text-align: center;
        }
        .footer-text {
            font-size: 11px;
            color: #555;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <!-- HEADER CON LOGO -->
    <div class="top-header">
        <img src="/assets/logo.png" alt="Logo" class="logo-img">
        <span class="brand-name">KALIROOT-AI</span>
    </div>
    
    <!-- USER HEADER -->
    <div class="user-header">
        <div class="avatar">{user_initial}</div>
        <div class="user-info">
            <h2>{user_name}</h2>
            <span class="badge">👑 ELITE MEMBER</span>
        </div>
    </div>
    
    <div class="main-content">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{modules_completed}</div>
                <div class="stat-label">Módulos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{credits}</div>
                <div class="stat-label">Créditos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{days_left}</div>
                <div class="stat-label">Días</div>
            </div>
        </div>
        
        <div class="section-title">📥 Recursos Exclusivos</div>
        <div class="resources-grid">
            <a href="https://drive.google.com/uc?export=download&id=1example1" class="resource-card">
                <div class="resource-icon">🐉</div>
                <div class="resource-title">Kali Pack</div>
                <div class="resource-desc">Configuraciones y scripts</div>
                <span class="resource-badge">2.3 GB</span>
            </a>
            <a href="https://drive.google.com/uc?export=download&id=1example2" class="resource-card">
                <div class="resource-icon">📱</div>
                <div class="resource-title">Termux Elite</div>
                <div class="resource-desc">Setup móvil completo</div>
                <span class="resource-badge">450 MB</span>
            </a>
            <a href="https://drive.google.com/uc?export=download&id=1example3" class="resource-card">
                <div class="resource-icon">📡</div>
                <div class="resource-title">WiFi Toolkit</div>
                <div class="resource-desc">Wordlists y scripts</div>
                <span class="resource-badge">1.8 GB</span>
            </a>
            <a href="https://drive.google.com/uc?export=download&id=1example4" class="resource-card">
                <div class="resource-icon">💉</div>
                <div class="resource-title">Web Pentest</div>
                <div class="resource-desc">Payloads XSS/SQLi</div>
                <span class="resource-badge">320 MB</span>
            </a>
        </div>
        
        <div class="section-title">⚡ Acciones Rápidas</div>
        <div class="action-list">
            <a href="/webapp/labs?token={token}" class="action-item">
                <div class="action-icon green">🧪</div>
                <div class="action-content">
                    <div class="action-title">Laboratorios</div>
                    <div class="action-subtitle">Practica en entornos reales</div>
                </div>
                <span class="action-arrow">›</span>
            </a>
            <a href="/webapp/learning?token={token}" class="action-item">
                <div class="action-icon blue">📚</div>
                <div class="action-content">
                    <div class="action-title">Mi Ruta de Aprendizaje</div>
                    <div class="action-subtitle">Continúa tu entrenamiento</div>
                </div>
                <span class="action-arrow">›</span>
            </a>
            <a href="#" class="action-item" onclick="goToBot('ai')">
                <div class="action-icon purple">🤖</div>
                <div class="action-content">
                    <div class="action-title">Asistente IA</div>
                    <div class="action-subtitle">Pregunta lo que quieras</div>
                </div>
                <span class="action-arrow">›</span>
            </a>
        </div>
    </div>
    
    <!-- BOTTOM BAR -->
    <div class="bottom-bar">
        <button class="bottom-btn secondary" onclick="closeApp()">Cerrar</button>
        <button class="bottom-btn primary" onclick="goToBot('menu')">📱 Ir al Bot</button>
    </div>
    
    <!-- FOOTER -->
    <div class="footer">
        <p class="footer-text">© 2026 KALIROOT-AI. Todos los derechos reservados.</p>
    </div>
    
    <script>
        var tg = window.Telegram && window.Telegram.WebApp;
        if (tg) { tg.ready(); tg.expand(); }
        
        function goToBot(action) {
            if (tg) {
                tg.close();
            }
        }
        
        function closeApp() {
            if (tg) tg.close();
        }
        
        // Handle resource downloads
        document.querySelectorAll('.resource-card').forEach(function(card) {
            card.addEventListener('click', function(e) {
                var url = this.getAttribute('href');
                if (url && tg) {
                    e.preventDefault();
                    tg.openLink(url);
                }
            });
        });
    </script>
</body>
</html>"""

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
@app.get("/webapp_v2", response_class=HTMLResponse)
async def webapp_entry():
    """Serves the loader which POSTs initData to /webapp/check for secure validation."""
    return HTMLResponse(content=HTML_LOADER, media_type="text/html; charset=utf-8")

import time

def create_token(user_id: int, is_premium: bool = False) -> str:
    """Creates a temporary signed token for the dashboard."""
    timestamp = int(time.time())
    status = "1" if is_premium else "0"
    payload = f"{user_id}:{timestamp}:{status}"
    signature = hmac.new(TELEGRAM_BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_token(token: str) -> tuple:
    """Verifies the token and returns (user_id, is_premium) if valid and not expired."""
    try:
        parts = token.split(':')
        if len(parts) != 4: return None, False
        user_id_str, timestamp_str, status, signature = parts
        
        # Check expiry (valid for 5 minutes for dashboard)
        if int(time.time()) - int(timestamp_str) > 300:
            return None, False
            
        # Verify signature
        payload = f"{user_id_str}:{timestamp_str}:{status}"
        expected_signature = hmac.new(TELEGRAM_BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str), status == "1"
        return None, False
    except Exception:
        return None, False

@app.post("/webapp/check")
async def webapp_check(request: Request):
    """Validates initData and returns a redirect URL with a signed token."""
    try:
        data = await request.json()
        init_data = data.get('initData')
        user_data = validate_telegram_data(init_data)
        
        if not user_data:
            return {"error": "Datos de sesión inválidos"}
            
        user_id = user_data.get('id')
        user_first_name = user_data.get('first_name', 'Usuario')
        
        # Register user if not exists
        from database_manager import register_user_if_not_exists
        await register_user_if_not_exists(user_id, first_name=user_first_name)
        
        # Check Subscription using the correct fields
        from database_manager import is_user_subscribed
        is_premium = await is_user_subscribed(user_id)
        
        # Create token with premium status
        token = create_token(user_id, is_premium)
        
        if is_premium:
            return {"redirect_url": f"/webapp/dashboard?token={token}"}
        else:
            return {"redirect_url": f"/webapp/upsell?token={token}"}
            
    except Exception as e:
        logger.exception(f"Webapp check error: {e}")
        return {"error": "Error de servidor"}

@app.get("/webapp/dashboard", response_class=HTMLResponse)
async def webapp_dashboard(token: str):
    """Serves the Premium Dashboard if token is valid and user is premium."""
    try:
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Sesión Expirada</h2><p style='color:#708499'>Vuelve a abrir la app desde el bot</p></div></body></html>", status_code=403, media_type="text/html; charset=utf-8")
        
        if not is_premium:
            # Redirect to upsell
            return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        # Fetch user data from Supabase with error handling
        user_name = "Elite"
        user_initial = "E"
        credits = 0
        completed_modules = []
        days_left = 0
        
        try:
            from database_manager import get_user_profile, get_user_credits, get_user_completed_modules
            
            profile = await get_user_profile(user_id)
            if profile:
                user_name = profile.get('first_name') or 'Elite'
                user_initial = user_name[0].upper() if user_name else 'E'
                
                # Calculate days left
                expiry_str = profile.get('subscription_expiry_date')
                if expiry_str:
                    try:
                        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        now = datetime.now(expiry.tzinfo)
                        delta = expiry - now
                        days_left = max(0, delta.days)
                    except:
                        days_left = 30  # Default
            
            credits = await get_user_credits(user_id) or 0
            completed_modules = await get_user_completed_modules(user_id) or []
            
        except Exception as e:
            logger.error(f"Error fetching user data for dashboard: {e}")
            # Continue with default values
        
        html = HTML_PREMIUM.replace("{user_name}", user_name)\
            .replace("{user_initial}", user_initial)\
            .replace("{modules_completed}", str(len(completed_modules)))\
            .replace("{credits}", str(credits))\
            .replace("{days_left}", str(days_left))\
            .replace("{token}", token)
        
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Dashboard error: {e}")
        return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Error</h2><p style='color:#708499'>Intenta abrir la app de nuevo</p></div></body></html>", status_code=500, media_type="text/html; charset=utf-8")

@app.get("/webapp/upsell", response_class=HTMLResponse)
async def webapp_upsell(token: str = ""):
    """Serves the subscription page for non-premium users."""
    try:
        user_id = 0
        logger.info(f"Upsell page requested with token length: {len(token) if token else 0}")
        
        if token:
            result = verify_token(token)
            logger.info(f"verify_token result: {result}")
            
            if result and result[0]:
                user_id = result[0]
                logger.info(f"Token verified successfully, user_id: {user_id}")
            else:
                logger.warning(f"Token verification failed, result: {result}")
        else:
            logger.warning("No token provided to upsell page")
        
        # Pass user_id to the HTML - invoice is created on-demand via API
        user_id_str = str(user_id) if user_id and user_id != 0 else "0"
        logger.info(f"Rendering upsell page with user_id: {user_id_str}")
        
        html = HTML_NO_PREMIUM.replace("{user_id}", user_id_str)
        
        # Add no-cache headers to prevent Telegram from caching old versions
        response = HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except Exception as e:
        logger.exception(f"Upsell page error: {e}")
        return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Error</h2><p style='color:#708499'>Usa /suscribirse en el bot</p></div></body></html>", status_code=500, media_type="text/html; charset=utf-8")

# API endpoint for creating payment invoices
@app.post("/api/create-invoice")
async def api_create_invoice(request: Request):
    """Creates a NOWPayments invoice for subscription or credits."""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        amount = data.get('amount', 10.0)
        payment_type = data.get('type', 'subscription')
        
        if not user_id or user_id == 0:
            return {"error": "User ID inválido"}
        
        logger.info(f"API: Creating invoice for user {user_id}, amount ${amount}, type {payment_type}")
        
        from nowpayments_handler import create_payment_invoice
        invoice = create_payment_invoice(amount, user_id, payment_type)
        
        if invoice and invoice.get('invoice_url'):
            logger.info(f"API: Invoice created successfully: {invoice['invoice_url'][:50]}...")
            
            # Store pending subscription
            try:
                from database_manager import set_subscription_pending
                await set_subscription_pending(user_id, str(invoice.get('invoice_id', '')))
            except Exception as e:
                logger.error(f"Error setting pending subscription: {e}")
            
            return {
                "success": True,
                "invoice_url": invoice['invoice_url'],
                "invoice_id": invoice['invoice_id']
            }
        else:
            logger.error(f"API: Invoice creation failed for user {user_id}")
            return {"error": "No se pudo crear el enlace de pago. Verifica la configuración de NOWPayments."}
            
    except Exception as e:
        logger.exception(f"API create-invoice error: {e}")
        return {"error": f"Error del servidor: {str(e)}"}

# --- LEARNING SYSTEM WEB APP ---

HTML_LEARNING_HOME = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ruta de Aprendizaje - KALIROOT-AI</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            padding-bottom: 150px;
            display: flex;
            flex-direction: column;
        }
        
        /* ===== HEADER CON LOGO ===== */
        .top-header {
            background: #0a0a0a;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            border-bottom: 1px solid rgba(51, 144, 236, 0.2);
        }
        .logo-img {
            width: 42px;
            height: 42px;
            border-radius: 10px;
            object-fit: contain;
        }
        .brand-name {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #3390ec, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* ===== HERO SECTION ===== */
        .hero-section {
            background: #0d0d0d;
            padding: 24px 16px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .hero-icon { font-size: 48px; margin-bottom: 12px; }
        .hero-section h1 { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
        .hero-subtitle { 
            color: #708499; 
            font-size: 14px;
        }
        
        .main-content {
            flex: 1;
        }
        
        .progress-bar-container {
            background: #111111;
            padding: 16px;
            margin: 16px;
            border-radius: 12px;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .progress-label span:first-child { color: #708499; }
        .progress-label span:last-child { 
            color: #3390ec;
            font-weight: 600;
        }
        .progress-track {
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            height: 8px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3390ec, #00d4aa);
            border-radius: 8px;
            transition: width 0.5s ease;
        }
        
        .section-list {
            padding: 0 16px;
        }
        .section-card {
            background: #111111;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            text-decoration: none;
            color: inherit;
            display: block;
            transition: transform 0.2s, box-shadow 0.2s;
            border-left: 4px solid transparent;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .section-card:active {
            transform: scale(0.98);
        }
        .section-card.unlocked {
            border-left-color: #3390ec;
        }
        .section-card.completed {
            border-left-color: #4ade80;
        }
        .section-card.locked {
            border-left-color: #708499;
            opacity: 0.7;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        .section-icon { font-size: 24px; }
        .section-info { flex: 1; }
        .section-title { 
            font-size: 15px; 
            font-weight: 600;
            margin-bottom: 4px;
        }
        .section-meta {
            font-size: 12px;
            color: #708499;
        }
        .section-status {
            font-size: 20px;
        }
        
        .section-progress {
            margin-top: 8px;
        }
        .mini-progress {
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            height: 4px;
            overflow: hidden;
        }
        .mini-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3390ec, #00d4aa);
            border-radius: 4px;
        }
        
        /* ===== BOTTOM NAV ===== */
        .bottom-nav {
            position: fixed;
            bottom: 50px;
            left: 0;
            right: 0;
            background: #0a0a0a;
            border-top: 1px solid rgba(51, 144, 236, 0.2);
            padding: 12px 16px;
            display: flex;
            gap: 8px;
        }
        .nav-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-decoration: none;
            transition: transform 0.2s, opacity 0.2s;
        }
        .nav-btn:active {
            transform: scale(0.98);
            opacity: 0.9;
        }
        .nav-btn.primary {
            background: #3390ec;
            color: #fff;
        }
        .nav-btn.secondary {
            background: rgba(51, 144, 236, 0.15);
            color: #3390ec;
            border: 1px solid rgba(51, 144, 236, 0.3);
        }
        
        /* ===== FOOTER ===== */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #050505;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 14px 16px;
            text-align: center;
        }
        .footer-text {
            font-size: 11px;
            color: #555;
            letter-spacing: 0.5px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid #708499;
            border-top-color: #3390ec;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <!-- HEADER CON LOGO -->
    <div class="top-header">
        <img src="/assets/logo.png" alt="Logo" class="logo-img">
        <span class="brand-name">KALIROOT-AI</span>
    </div>
    
    <!-- HERO SECTION -->
    <div class="hero-section">
        <div class="hero-icon">🗺️</div>
        <h1>Ruta de Aprendizaje</h1>
        <p class="hero-subtitle">Domina las 10 fases del Hacking Ético</p>
    </div>
    
    <div class="main-content">
        <div class="progress-bar-container">
            <div class="progress-label">
                <span>Progreso Total</span>
                <span id="progress-text">{completed}/{total} Módulos</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="width: {progress_percent}%"></div>
            </div>
        </div>
        
        <div class="section-list" id="sections">
            {sections_html}
        </div>
    </div>
    
    <!-- BOTTOM NAV -->
    <div class="bottom-nav">
        <a href="/webapp/dashboard?token={token}" class="nav-btn secondary">← Dashboard</a>
        <button class="nav-btn primary" id="continueBtn">▶️ Continuar</button>
    </div>
    
    <!-- FOOTER -->
    <div class="footer">
        <p class="footer-text">© 2026 KALIROOT-AI. Todos los derechos reservados.</p>
    </div>
    
    <script>
        var tg = window.Telegram && window.Telegram.WebApp;
        if (tg) { tg.ready(); tg.expand(); }
        
        document.getElementById('continueBtn').addEventListener('click', function() {
            var nextModule = {next_module};
            if (nextModule > 0) {
                window.location.href = '/webapp/learning/module/' + nextModule + '?token={token}';
            }
        });
    </script>
</body>
</html>"""

HTML_LEARNING_SECTION = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{section_title} - KALIROOT-AI</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            padding-bottom: 150px;
            display: flex;
            flex-direction: column;
        }
        
        /* ===== HEADER CON LOGO ===== */
        .top-header {
            background: #0a0a0a;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            border-bottom: 1px solid rgba(51, 144, 236, 0.2);
        }
        .logo-img {
            width: 42px;
            height: 42px;
            border-radius: 10px;
            object-fit: contain;
        }
        .brand-name {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #3390ec, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* ===== SECTION HEADER ===== */
        .section-header {
            background: #0d0d0d;
            padding: 20px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .back-link {
            color: #3390ec;
            text-decoration: none;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-bottom: 12px;
        }
        .section-header h1 { 
            font-size: 20px; 
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header-desc {
            color: #708499;
            font-size: 13px;
            margin-top: 8px;
        }
        
        .main-content {
            flex: 1;
        }
        
        .module-list {
            padding: 16px;
        }
        .module-card {
            background: #111111;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 10px;
            text-decoration: none;
            color: inherit;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: transform 0.2s;
            border: 1px solid rgba(51, 144, 236, 0.1);
        }
        .module-card:active { transform: scale(0.98); }
        .module-card.locked {
            opacity: 0.5;
            pointer-events: none;
        }
        
        .module-thumb {
            width: 50px;
            height: 50px;
            border-radius: 10px;
            object-fit: cover;
            border: 1px solid rgba(51, 144, 236, 0.2);
        }
        
        .module-number {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
        }
        .module-number.unlocked {
            background: rgba(51, 144, 236, 0.2);
            color: #3390ec;
        }
        .module-number.completed {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }
        .module-number.locked {
            background: rgba(112, 132, 153, 0.2);
            color: #708499;
        }
        
        .module-info { flex: 1; }
        .module-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .module-desc {
            font-size: 12px;
            color: #708499;
        }
        .module-status { font-size: 18px; }
        
        /* ===== BOTTOM NAV ===== */
        .bottom-nav {
            position: fixed;
            bottom: 50px;
            left: 0;
            right: 0;
            background: #0a0a0a;
            border-top: 1px solid rgba(51, 144, 236, 0.2);
            padding: 12px 16px;
        }
        .nav-btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            background: #3390ec;
            color: #fff;
            text-decoration: none;
            display: block;
            text-align: center;
            transition: transform 0.2s, opacity 0.2s;
        }
        .nav-btn:active {
            transform: scale(0.98);
            opacity: 0.9;
        }
        
        /* ===== FOOTER ===== */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #050505;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 14px 16px;
            text-align: center;
        }
        .footer-text {
            font-size: 11px;
            color: #555;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <!-- HEADER CON LOGO -->
    <div class="top-header">
        <img src="/assets/logo.png" alt="Logo" class="logo-img">
        <span class="brand-name">KALIROOT-AI</span>
    </div>
    
    <!-- SECTION HEADER -->
    <div class="section-header">
        <a href="/webapp/learning?token={token}" class="back-link">← Volver a Secciones</a>
        <h1>{section_icon} {section_title}</h1>
        <p class="header-desc">{section_progress} módulos completados</p>
    </div>
    
    <div class="main-content">
        <div class="module-list">
            {modules_html}
        </div>
    </div>
    
    <!-- BOTTOM NAV -->
    <div class="bottom-nav">
        <a href="/webapp/learning?token={token}" class="nav-btn">🗺️ Ver Mapa Completo</a>
    </div>
    
    <!-- FOOTER -->
    <div class="footer">
        <p class="footer-text">© 2026 KALIROOT-AI. Todos los derechos reservados.</p>
    </div>
    
    <script>
        var tg = window.Telegram && window.Telegram.WebApp;
        if (tg) { tg.ready(); tg.expand(); }
    </script>
</body>
</html>"""

HTML_LEARNING_MODULE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Módulo {module_id} - KALIROOT-AI</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #000000;
            --card-bg: #111111;
            --text: #ffffff;
            --hint: #708499;
            --button: #3390ec;
            --button-text: #ffffff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text);
            padding-bottom: 180px;
            display: flex;
            flex-direction: column;
        }
        
        /* ===== HEADER CON LOGO ===== */
        .top-header {
            background: #0a0a0a;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            border-bottom: 1px solid rgba(51, 144, 236, 0.2);
            position: sticky;
            top: 0;
            z-index: 50;
        }
        .logo-img {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            object-fit: contain;
        }
        .brand-name {
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 1px;
            background: linear-gradient(135deg, #3390ec, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* ===== MODULE HERO IMAGE ===== */
        .header-image {
            width: 100%;
            height: 220px;
            background-image: url('{module_image}');
            background-size: cover;
            background-position: center;
            position: relative;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        .header-overlay {
            position: absolute; inset: 0;
            background: linear-gradient(to top, var(--bg-color) 0%, rgba(0,0,0,0.6) 50%, rgba(0,0,0,0.3) 100%);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 24px;
        }
        
        .module-badge {
            background: rgba(51, 144, 236, 0.2);
            color: var(--button);
            backdrop-filter: blur(8px);
            font-size: 11px;
            font-weight: 800;
            padding: 6px 14px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
            align-self: flex-start;
            margin-bottom: 12px;
            border: 1px solid rgba(51, 144, 236, 0.3);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .module-badge.completed {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
            border-color: rgba(74, 222, 128, 0.3);
        }
        
        h1 { 
            font-size: 24px; 
            font-weight: 800; 
            line-height: 1.2;
            text-shadow: 0 2px 10px rgba(0,0,0,0.5);
            margin: 0;
        }
        
        .main-content {
            flex: 1;
        }
        
        .hero-desc {
            color: var(--hint);
            font-size: 15px;
            line-height: 1.6;
            padding: 20px 24px;
            background: #0d0d0d;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        /* AI Content */
        #ai-content { padding: 20px 24px; min-height: 200px; }
        
        .content-block { margin-bottom: 25px; animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
        .section-title {
            color: var(--button);
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex; align-items: center; gap: 10px;
            letter-spacing: 0.5px;
        }
        
        p { 
            line-height: 1.7; 
            font-size: 16px; 
            color: var(--text); 
            opacity: 0.9;
            margin-bottom: 16px; 
        }
        
        /* Code */
        pre {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 18px;
            overflow-x: auto;
            border: 1px solid rgba(51, 144, 236, 0.1);
            margin: 20px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
        }
        code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #58a6ff;
        }
        
        /* Tip Box */
        .tip-box {
            background: rgba(51, 144, 236, 0.08);
            border-left: 3px solid var(--button);
            padding: 16px;
            border-radius: 8px;
            margin: 24px 0;
        }
        
        .regen-btn {
            background: transparent;
            border: 1px solid var(--hint);
            color: var(--hint);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            margin: 40px auto 20px;
            display: block;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        .regen-btn:active {
            opacity: 1;
        }

        /* ===== BOTTOM ACTIONS ===== */
        .bottom-actions {
            position: fixed; bottom: 50px; left: 0; right: 0;
            background: #0a0a0a;
            backdrop-filter: blur(16px);
            padding: 16px 24px 20px 24px;
            border-top: 1px solid rgba(51, 144, 236, 0.2);
            z-index: 100;
            display: flex; flex-direction: column; gap: 12px;
            box-shadow: 0 -4px 30px rgba(0,0,0,0.3);
        }
        
        .action-btn {
            width: 100%; 
            padding: 16px; 
            border: none; 
            border-radius: 14px;
            font-size: 16px; font-weight: 700; 
            cursor: pointer;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s;
            position: relative; overflow: hidden;
            text-decoration: none;
        }
        .action-btn:active { transform: scale(0.96); opacity: 0.9; }
        
        .action-btn.primary { 
            background: var(--button); 
            color: var(--button-text); 
            box-shadow: 0 8px 20px rgba(51, 144, 236, 0.3);
        }
        .action-btn.success {
            background: #4ade80; color: #002b10;
            box-shadow: 0 8px 20px rgba(74, 222, 128, 0.3);
        }
        .action-btn.secondary {
            background: rgba(51, 144, 236, 0.15);
            color: var(--button);
            font-size: 14px;
            padding: 14px;
            border: 1px solid rgba(51, 144, 236, 0.3);
        }
        
        /* ===== FOOTER ===== */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #050505;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 14px 16px;
            text-align: center;
            z-index: 101;
        }
        .footer-text {
            font-size: 11px;
            color: #555;
            letter-spacing: 0.5px;
        }

        /* Spinner */
        .loading-container { text-align: center; padding: 60px 20px; }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: var(--button);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <!-- HEADER CON LOGO -->
    <div class="top-header">
        <img src="/assets/logo.png" alt="Logo" class="logo-img">
        <span class="brand-name">KALIROOT-AI</span>
    </div>
    
    <!-- MODULE HERO IMAGE -->
    <div class="header-image">
        <div class="header-overlay">
            <div class="module-badge {badge_class}">Módulo {module_id}</div>
            <h1>{module_title}</h1>
        </div>
    </div>
    
    <div class="main-content">
        <p class="hero-desc">{module_desc}</p>

        <div id="ai-content">
            <div class="loading-container">
                <div class="spinner"></div>
                <div style="color: var(--hint); font-size: 14px;">Contactando con KALIROOT-AI...</div>
            </div>
        </div>
        
        <button class="regen-btn" onclick="loadContent(true)">🔄 Actualizar Contenido</button>
    </div>

    <!-- BOTTOM ACTIONS -->
    <div class="bottom-actions">
        <div id="statusMsg" style="text-align: center; font-size: 13px; margin-bottom: 8px; display: none;"></div>
        
        {complete_button}
        
        <div class="nav-row" style="display: flex; gap: 12px;">
            <button class="action-btn secondary" onclick="window.location.href='/webapp/learning?token={token}'" style="flex: 0 0 60px; font-size: 20px;">🏠</button>
            {prev_button}
            {next_button}
        </div>
    </div>
    
    <!-- FOOTER -->
    <div class="footer">
        <p class="footer-text">© 2026 KALIROOT-AI. Todos los derechos reservados.</p>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.enableClosingConfirmation();
        
        const moduleId = {module_id};
        const token = "{token}";
        const contentDiv = document.getElementById('ai-content');
        
        function loadContent(force = false) {
            if(force) {
                 contentDiv.innerHTML = `
                <div class="loading-container">
                    <div class="spinner"></div>
                    <div style="color: var(--hint);">Regenerando...</div>
                </div>`;
            }
            
            fetch('/api/learning/get_content', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ token: token, module_id: moduleId, force: force })
            })
            .then(r => r.json())
            .then(data => {
                if(data.success) {
                    contentDiv.innerHTML = data.html;
                } else {
                    contentDiv.innerHTML = `<div class="tip-box" style="border-color: #ff4757; background: rgba(255, 71, 87, 0.1);">
                        <p style="color:#ff4757; font-weight:bold;">⚠️ Error de Sistema</p>
                        <p>${data.error}</p>
                        <button class="regen-btn" onclick="loadContent(true)">Reintentar</button>
                    </div>`;
                }
            })
            .catch(e => {
                contentDiv.innerHTML = '<div style="text-align:center; padding: 20px;">Error de conexión.</div>';
            });
        }
        
        // Initial load
        loadContent();

        // Complete Logic
        const completeBtn = document.getElementById('completeBtn');
        if(completeBtn) {
            completeBtn.addEventListener('click', () => {
                const status = document.getElementById('statusMsg');
                
                completeBtn.disabled = true;
                completeBtn.style.opacity = '0.7';
                completeBtn.innerText = '⌛ Procesando...';
                
                fetch('/webapp/learning/complete_module/' + moduleId + '?token=' + token)
                .then(r => r.json())
                .then(d => {
                    if(d.ok) {
                        status.style.display = 'block';
                        status.style.color = '#4ade80';
                        status.innerText = '✅ Módulo completado. +XP';
                        tg.HapticFeedback.notificationOccurred('success');
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        status.innerText = '⚠️ Error.';
                        status.style.display = 'block';
                        status.style.color = '#ff4757';
                        completeBtn.disabled = false;
                        completeBtn.innerText = '✅ Marcar como Completado';
                    }
                })
                .catch(e => {
                    status.innerText = '⚠️ Error.';
                    status.style.display = 'block';
                    completeBtn.disabled = false;
                });
            });
        }
    </script>
</body>
</html>"""

# Learning Routes - PREMIUM ONLY

HTML_LABS_HOME = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Laboratorios - KaliRoot</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--tg-theme-bg-color, #17212b); color: var(--tg-theme-text-color, #fff); padding: 16px; margin: 0; padding-bottom: 80px; }
        .hero { text-align: center; margin-bottom: 24px; padding: 16px 0; }
        .hero h1 { font-size: 24px; margin-bottom: 8px; margin-top: 0; }
        .hero p { color: var(--tg-theme-hint-color, #aaa); font-size: 14px; margin: 0; }
        
        .cat-card { background: var(--tg-theme-secondary-bg-color, #232e3c); padding: 16px; border-radius: 12px; margin-bottom: 12px; display: block; text-decoration: none; color: inherit; }
        .cat-header { display: flex; align-items: center; margin-bottom: 12px; }
        .cat-icon { font-size: 24px; margin-right: 12px; width: 40px; height: 40px; background: rgba(51, 144, 236, 0.1); display: flex; align-items: center; justify-content: center; border-radius: 8px; }
        .cat-title { font-weight: 600; font-size: 16px; flex: 1; }
        .cat-count { font-size: 12px; color: var(--tg-theme-hint-color, #708499); background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 10px; }
        
        .progress-bar { height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; background: #4ade80; width: 0%; transition: width 0.3s ease; }
        
        .lab-list { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); display: none; }
        .lab-item { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-decoration: none; color: inherit; }
        .lab-item:last-child { border-bottom: none; }
        .lab-status { margin-right: 12px; font-size: 18px; }
        .lab-info { flex: 1; }
        .lab-name { font-size: 14px; font-weight: 500; }
        .lab-xp { font-size: 11px; color: #4ade80; }
        
        .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: var(--tg-theme-secondary-bg-color, #232e3c); padding: 12px; display: flex; justify-content: center; border-top: 1px solid rgba(255,255,255,0.05); }
        .back-btn { background: none; border: none; color: var(--tg-theme-button-color, #3390ec); font-weight: 600; cursor: pointer; font-size: 15px; }
        
        /* Accordion logic */
        .cat-card.active .lab-list { display: block; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>🧪 Laboratorios Prácticos</h1>
        <p>100 Escenarios de Ciberseguridad</p>
    </div>
    <div id="categories">
        {categories_html}
    </div>
    <div class="bottom-nav">
        <button class="back-btn" onclick="window.location.href='/webapp/dashboard?token={token}'">🏠 Volver al Dashboard</button>
    </div>
    <script>
        var tg = window.Telegram.WebApp;
        tg.expand();
        
        function toggleCat(id) {
            const el = document.getElementById('cat-' + id);
            el.classList.toggle('active');
        }
    </script>
</body>
</html>
"""

HTML_LAB_DETAIL = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Lab - KaliRoot</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--tg-theme-bg-color, #17212b); color: var(--tg-theme-text-color, #fff); padding: 16px; margin: 0; padding-bottom: 100px; }
        
        .lab-header { margin-bottom: 24px; }
        .lab-badge { display: inline-block; padding: 4px 10px; background: rgba(51, 144, 236, 0.15); color: #3390ec; border-radius: 6px; font-size: 12px; font-weight: 600; margin-bottom: 10px; }
        .lab-title { font-size: 22px; font-weight: 700; margin-bottom: 8px; line-height: 1.3; }
        
        .mission-box { background: var(--tg-theme-secondary-bg-color, #232e3c); padding: 16px; border-radius: 12px; margin-bottom: 24px; border-left: 4px solid #facc15; }
        .mission-title { font-weight: 700; font-size: 13px; color: #facc15; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        .mission-text { font-size: 15px; line-height: 1.5; }
        
        .terminal { background: #1a1b1e; color: #4ade80; padding: 16px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 13px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.1); position: relative; min-height: 120px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .terminal-header { color: #555; font-size: 11px; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; display: flex; justify-content: space-between; }
        .cmd { color: #fff; font-weight: bold; }
        .prompt { color: #4ade80; }
        .output { color: #aaa; white-space: pre-wrap; margin-top: 12px; line-height: 1.4; }
        
        .challenge-box { margin-bottom: 24px; animation: fadeIn 0.5s; }
        .question { font-weight: 600; margin-bottom: 12px; font-size: 15px; }
        
        .input-group { display: flex; gap: 10px; margin-top: 12px; }
        input { flex: 1; padding: 12px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: var(--tg-theme-bg-color, #17212b); color: #fff; outline: none; font-size: 15px; }
        input:focus { border-color: #3390ec; background: rgba(51, 144, 236, 0.05); }
        .check-btn { background: var(--tg-theme-button-color, #3390ec); color: var(--tg-theme-button-text-color, #fff); border: none; padding: 0 20px; border-radius: 10px; font-weight: 600; cursor: pointer; font-size: 15px; }
        
        .result-msg { margin-top: 16px; padding: 12px; border-radius: 10px; display: none; text-align: center; font-weight: 500; font-size: 14px; }
        .result-msg.success { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.2); }
        .result-msg.error { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.2); }
        
        .run-btn { background: var(--tg-theme-secondary-bg-color, #232e3c); color: #fff; border: 1px solid rgba(51, 144, 236, 0.5); width: 100%; padding: 16px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 16px; font-size: 15px; font-weight: 600; transition: all 0.2s; }
        .run-btn:active { transform: scale(0.98); }
        
        .nav-actions { margin-top: 32px; text-align: center; }
        .nav-link { color: var(--tg-theme-hint-color, #708499); text-decoration: none; font-size: 14px; display: inline-flex; align-items: center; gap: 6px; }
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="lab-header">
        <div class="lab-badge">LAB {lab_id} • {category}</div>
        <div class="lab-title">{title}</div>
    </div>
    
    <div class="mission-box">
        <div class="mission-title">🕵️ Misión de Inteligencia</div>
        <div class="mission-text">{mission}</div>
    </div>
    
    <button class="run-btn" id="runCmdBtn">
        <span>⚡</span> Ejecutar Comando en Terminal
    </button>
    
    <div class="terminal" id="terminal" style="display:none;">
        <div class="terminal-header">
            <span>kali@root: ~</span>
            <span>bash</span>
        </div>
        <div><span class="prompt">root@kali:~#</span> <span class="cmd" id="cmdText"></span><span class="cursor">_</span></div>
        <div class="output" id="cmdOutput"></div>
    </div>
    
    <div class="challenge-box" id="challengeBox" style="display:none;">
        <div class="question">❓ {question}</div>
        <div class="input-group">
            <input type="text" id="flagInput" placeholder="Ingresa la respuesta aquí..." autocomplete="off">
            <button class="check-btn" id="checkBtn">Enviar</button>
        </div>
        <div class="result-msg" id="resultMsg"></div>
    </div>
    
    <div class="nav-actions">
        <a href="/webapp/labs?token={token}" class="nav-link">
            <span>←</span> Volver a Lista de Laboratorios
        </a>
    </div>

    <script>
        var tg = window.Telegram.WebApp;
        tg.expand();
        
        const labData = {
            command: "{command}",
            output: `{output}`,
            labId: {lab_id},
            token: "{token}"
        };
        
        const runBtn = document.getElementById('runCmdBtn');
        const terminal = document.getElementById('terminal');
        const cmdText = document.getElementById('cmdText');
        const cmdOutput = document.getElementById('cmdOutput');
        const challengeBox = document.getElementById('challengeBox');
        
        runBtn.addEventListener('click', () => {
            runBtn.style.display = 'none';
            terminal.style.display = 'block';
            
            // Typewriter effect
            let i = 0;
            const txt = labData.command;
            const speed = 40;
            
            function typeWriter() {
                if (i < txt.length) {
                    cmdText.innerHTML += txt.charAt(i);
                    i++;
                    setTimeout(typeWriter, speed);
                } else {
                    document.querySelector('.cursor').style.display = 'none';
                    setTimeout(() => {
                        cmdOutput.innerText = labData.output;
                        challengeBox.style.display = 'block';
                        tg.HapticFeedback.notificationOccurred('success');
                    }, 400);
                }
            }
            typeWriter();
        });
        
        document.getElementById('checkBtn').addEventListener('click', () => {
            const flag = document.getElementById('flagInput').value;
            const resultMsg = document.getElementById('resultMsg');
            const btn = document.getElementById('checkBtn');
            const input = document.getElementById('flagInput');
            
            if(!flag) return;
            
            btn.disabled = true;
            btn.style.opacity = '0.7';
            
            fetch('/api/labs/check', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ token: labData.token, lab_id: labData.labId, flag: flag })
            })
            .then(r => r.json())
            .then(data => {
                btn.disabled = false;
                btn.style.opacity = '1';
                resultMsg.style.display = 'block';
                
                if(data.success) {
                    resultMsg.className = 'result-msg success';
                    resultMsg.innerHTML = '🎉 ¡Misión Cumplida! +' + data.xp + ' XP';
                    input.disabled = true;
                    tg.HapticFeedback.notificationOccurred('success');
                    
                    setTimeout(() => {
                        window.location.href = '/webapp/labs?token=' + labData.token;
                    }, 2500);
                } else {
                    resultMsg.className = 'result-msg error';
                    resultMsg.innerText = '⚠️ Respuesta Incorrecta. Inténtalo de nuevo.';
                    tg.HapticFeedback.notificationOccurred('error');
                    input.value = '';
                    input.focus();
                }
            });
        });
    </script>
</body>
</html>
"""
@app.get("/webapp/learning", response_class=HTMLResponse)
async def webapp_learning(token: str = ""):
    """Main learning route showing all sections. PREMIUM ONLY."""
    try:
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Sesión Expirada</h2><p style='color:#708499'>Vuelve a abrir la app desde el bot</p></div></body></html>", status_code=403)
        
        # PREMIUM CHECK
        if not is_premium:
            return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        from learning_content import SECTIONS, MODULES
        from database_manager import get_user_completed_modules
        
        completed = await get_user_completed_modules(user_id) or []
        total_modules = len(MODULES)
        progress_percent = int((len(completed) / total_modules) * 100) if total_modules > 0 else 0
        
        # Find next module
        next_module = 1
        for i in range(1, 101):
            if i not in completed:
                next_module = i
                break
        
        # Generate sections HTML
        sections_html = ""
        for sec_id, data in SECTIONS.items():
            is_free = data['free']
            
            # Calculate section progress
            sec_mods = [k for k in MODULES if MODULES[k]['section'] == sec_id]
            sec_completed = len([m for m in sec_mods if m in completed])
            total_sec = len(sec_mods)
            sec_progress = int((sec_completed / total_sec) * 100) if total_sec > 0 else 0
            
            # Determine status
            if sec_completed == total_sec:
                status_icon = "✅"
                status_class = "completed"
            elif is_free or is_premium:
                status_icon = "🔓"
                status_class = "unlocked"
            else:
                status_icon = "🔒"
                status_class = "locked"
            
            sections_html += f'''
            <a href="/webapp/learning/section/{sec_id}?token={token}" class="section-card {status_class}">
                <div class="section-header">
                    <span class="section-icon">{data['title'].split()[0]}</span>
                    <div class="section-info">
                        <div class="section-title">{' '.join(data['title'].split()[1:])}</div>
                        <div class="section-meta">{sec_completed}/{total_sec} módulos</div>
                    </div>
                    <span class="section-status">{status_icon}</span>
                </div>
                <div class="section-progress">
                    <div class="mini-progress">
                        <div class="mini-progress-fill" style="width: {sec_progress}%"></div>
                    </div>
                </div>
            </a>
            '''
        
        html = HTML_LEARNING_HOME.replace("{sections_html}", sections_html)\
            .replace("{completed}", str(len(completed)))\
            .replace("{total}", str(total_modules))\
            .replace("{progress_percent}", str(progress_percent))\
            .replace("{next_module}", str(next_module))\
            .replace("{token}", token)
        
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Learning home error: {e}")
        return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Error</h2><p style='color:#708499'>Intenta abrir la app de nuevo</p></div></body></html>", status_code=500)

@app.get("/webapp/learning/section/{section_id}", response_class=HTMLResponse)
async def webapp_learning_section(section_id: int, token: str = ""):
    """Shows modules in a specific section. PREMIUM ONLY."""
    try:
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Sesión Expirada</h2></div></body></html>", status_code=403)
        
        # PREMIUM CHECK
        if not is_premium:
            return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        from learning_content import SECTIONS, MODULES
        from database_manager import get_user_completed_modules
        
        if section_id not in SECTIONS:
            return HTMLResponse(content="<html><body>Sección no encontrada</body></html>", status_code=404)
        
        section = SECTIONS[section_id]
        completed = await get_user_completed_modules(user_id) or []
        
        # No need to check section access since all sections are premium now
        
        # Get modules for this section
        section_modules = [(mod_id, mod) for mod_id, mod in MODULES.items() if mod['section'] == section_id]
        section_modules.sort(key=lambda x: x[0])
        
        sec_completed = len([m_id for m_id, _ in section_modules if m_id in completed])
        
        # Generate modules HTML
        modules_html = ""
        for mod_id, mod in section_modules:
            if mod_id in completed:
                status_icon = "✅"
                status_class = "completed"
            elif mod_id == 1 or (mod_id - 1) in completed:
                status_icon = "▶️"
                status_class = "unlocked"
            else:
                status_icon = "🔒"
                status_class = "locked"
            
            locked_class = "locked" if status_class == "locked" else ""
            
            modules_html += f'''
            <a href="/webapp/learning/module/{mod_id}?token={token}" class="module-card {locked_class}">
                <div class="module-number {status_class}">{mod_id}</div>
                <div class="module-info">
                    <div class="module-title">{mod['title']}</div>
                    <div class="module-desc">{mod['desc']}</div>
                </div>
                <span class="module-status">{status_icon}</span>
            </a>
            '''
        
        html = HTML_LEARNING_SECTION.replace("{modules_html}", modules_html)\
            .replace("{section_title}", ' '.join(section['title'].split()[1:]))\
            .replace("{section_icon}", section['title'].split()[0])\
            .replace("{section_progress}", f"{sec_completed}/{len(section_modules)}")\
            .replace("{token}", token)
        
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Learning section error: {e}")
        return HTMLResponse(content="<html><body>Error</body></html>", status_code=500)

@app.get("/webapp/learning/module/{module_id}", response_class=HTMLResponse)
async def webapp_learning_module(module_id: int, token: str = ""):
    """Shows a specific module's content. PREMIUM ONLY."""
    try:
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Sesión Expirada</h2></div></body></html>", status_code=403)
        
        # PREMIUM CHECK
        if not is_premium:
            return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        from learning_content import SECTIONS, MODULES
        from database_manager import get_user_completed_modules
        
        if module_id not in MODULES:
            return HTMLResponse(content="<html><body>Módulo no encontrado</body></html>", status_code=404)
        
        module = MODULES[module_id]
        section = SECTIONS[module['section']]
        completed = await get_user_completed_modules(user_id) or []
        
        # Check sequential access
        first_incomplete = 1
        for i in range(1, 101):
            if i not in completed:
                first_incomplete = i
                break
        
        if module_id > first_incomplete and module_id not in completed:
            return HTMLResponse(content=f"<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>🔒 Módulo Bloqueado</h2><p style='color:#708499'>Completa el módulo {first_incomplete} primero</p><a href='/webapp/learning/module/{first_incomplete}?token={token}' style='color:#3390ec;display:block;margin-top:16px'>Ir al Módulo {first_incomplete}</a></div></body></html>")
        
        is_completed = module_id in completed
        badge_class = "completed" if is_completed else ""
        
        # Complete button
        if is_completed:
            complete_button = '<button class="action-btn success" disabled>✅ Completado</button>'
        else:
            complete_button = '<button class="action-btn primary" id="completeBtn">✅ Marcar como Completado</button>'
        
        # Navigation buttons
        prev_button = ""
        next_button = ""
        
        if module_id > 1:
            prev_button = f'<a href="/webapp/learning/module/{module_id - 1}?token={token}" class="action-btn secondary">← Anterior</a>'
        else:
            prev_button = '<button class="action-btn secondary" disabled>← Anterior</button>'
        
        if module_id < 100:
            if is_completed or module_id + 1 in completed:
                next_button = f'<a href="/webapp/learning/module/{module_id + 1}?token={token}" class="action-btn secondary">Siguiente →</a>'
            else:
                next_button = '<button class="action-btn secondary" disabled>Siguiente →</button>'
        else:
            next_button = '<button class="action-btn secondary" disabled>Siguiente →</button>'
        
        html = HTML_LEARNING_MODULE.replace("{module_id}", str(module_id))\
            .replace("{module_title}", module['title'])\
            .replace("{module_desc}", module['desc'])\
            .replace("{module_image}", "/" + module['img'])\
            .replace("{badge_class}", badge_class)\
            .replace("{complete_button}", complete_button)\
            .replace("{prev_button}", prev_button)\
            .replace("{next_button}", next_button)\
            .replace("{token}", token)
        
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Learning module error: {e}")
        return HTMLResponse(content="<html><body>Error</body></html>", status_code=500)

@app.post("/api/learning/complete")
async def api_learning_complete(request: Request):
    """API endpoint to mark a module as completed."""
    try:
        data = await request.json()
        token = data.get('token', '')
        module_id = data.get('module_id')
        
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return {"success": False, "error": "Sesión expirada"}
        
        if not module_id:
            return {"success": False, "error": "Módulo inválido"}
        
        from database_manager import mark_module_completed, get_user_completed_modules
        from learning_content import MODULES
        
        # Mark as completed
        success = await mark_module_completed(user_id, module_id)
        
        if success:
            # Calculate XP (simple formula)
            xp_gained = 50 + (module_id * 2)  # More XP for later modules
            
            # Try to add XP
            try:
                from database_manager import add_xp
                await add_xp(user_id, xp_gained)
            except Exception as e:
                logger.warning(f"Could not add XP: {e}")
            
            # Find next module
            completed = await get_user_completed_modules(user_id) or []
            next_module = None
            if module_id < 100 and (module_id + 1) not in completed:
                next_module = module_id + 1
            
            return {
                "success": True,
                "xp": xp_gained,
                "next_module": next_module
            }
        else:
            return {"success": False, "error": "Error al guardar progreso"}
        
    except Exception as e:
        logger.exception(f"API learning complete error: {e}")
        return {"success": False, "error": "Error del servidor"}

@app.get("/api/learning/progress")
async def api_learning_progress(token: str = ""):
    """API endpoint to get user's learning progress."""
    try:
        user_id, is_premium = verify_token(token)
        
        if not user_id:
            return {"error": "Sesión expirada"}
        
        from database_manager import get_user_completed_modules
        from learning_content import SECTIONS, MODULES
        
        completed = await get_user_completed_modules(user_id) or []
        
        sections_progress = {}
        for sec_id, data in SECTIONS.items():
            sec_mods = [k for k in MODULES if MODULES[k]['section'] == sec_id]
            sec_completed = len([m for m in sec_mods if m in completed])
            sections_progress[sec_id] = {
                "title": data['title'],
                "completed": sec_completed,
                "total": len(sec_mods),
                "is_free": data['free']
            }
        
        return {
            "user_id": user_id,
            "is_premium": is_premium,
            "total_completed": len(completed),
            "total_modules": len(MODULES),
            "completed_modules": completed,
            "sections": sections_progress
        }
        
    except Exception as e:
        logger.exception(f"API learning progress error: {e}")
        return {"error": "Error del servidor"}

# ==========================================
# 🧪 LABS ROUTES (PREMIUM ONLY)
# ==========================================

@app.get("/webapp/labs", response_class=HTMLResponse)
async def webapp_labs(token: str = ""):
    """Labs Dashboard showing categories and progress."""
    try:
        user_id, is_premium = verify_token(token)
        if not user_id:
            return HTMLResponse(content="<html><body style='background:#17212b;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif'><div style='text-align:center'><h2>⚠️ Sesión Expirada</h2></div></body></html>", status_code=403)
        
        # PREMIUM CHECK
        if not is_premium:
            return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        from labs_content import LAB_CATEGORIES, LABS
        from database_manager import get_user_completed_labs
        
        completed = await get_user_completed_labs(user_id) or []
        
        categories_html = ""
        
        # Organize labs by category
        labs_by_cat = {cat_key: [] for cat_key in LAB_CATEGORIES}
        for lid, lab in LABS.items():
            labs_by_cat[lab['cat']].append((lid, lab))
            
        for cat_key, cat_name in LAB_CATEGORIES.items():
            cat_labs = labs_by_cat.get(cat_key, [])
            if not cat_labs: continue
            
            # Category Progress
            cat_completed_count = len([l for l in cat_labs if l[0] in completed])
            total_cat = len(cat_labs)
            progress_pct = int((cat_completed_count / total_cat) * 100) if total_cat > 0 else 0
            
            # Simple icon logic based on category name
            icon = "🐧"
            if "network" in cat_key: icon = "🌐"
            elif "web" in cat_key: icon = "🌍"
            elif "crypto" in cat_key: icon = "🔐"
            elif "forensics" in cat_key: icon = "🕵️‍♂️"
            elif "osint" in cat_key: icon = "👁️"
            elif "privesc" in cat_key: icon = "👑"
            elif "wifi" in cat_key: icon = "📡"
            elif "mobile" in cat_key: icon = "📱"
            elif "malware" in cat_key: icon = "🦠"
            
            # Generate Labs List HTML for this category (Hidden by default)
            lab_list_html = '<div class="lab-list">'
            for lid, lab in cat_labs:
                is_done = lid in completed
                status_icon = "✅" if is_done else "🔒" # Using padlock for todo, tick for done
                
                lab_list_html += f'''
                <a href="/webapp/labs/{lid}?token={token}" class="lab-item">
                    <div class="lab-status">{status_icon}</div>
                    <div class="lab-info">
                        <div class="lab-name">Lab {lid}: {lab['title']}</div>
                        <div class="lab-xp">+{lab['xp']} XP</div>
                    </div>
                    <div style="color:#3390ec">›</div>
                </a>
                '''
            lab_list_html += '</div>'
            
            categories_html += f'''
            <div class="cat-card" id="cat-{cat_key}" onclick="toggleCat('{cat_key}')">
                <div>
                    <div class="cat-header">
                        <div class="cat-icon">{icon}</div>
                        <div class="cat-title">{cat_name.split(' ', 1)[1] if ' ' in cat_name else cat_name}</div>
                        <div class="cat-count">{cat_completed_count}/{total_cat}</div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progress_pct}%"></div>
                    </div>
                    {lab_list_html}
                </div>
            </div>
            '''
            
        html = HTML_LABS_HOME.replace("{categories_html}", categories_html)\
            .replace("{token}", token)
            
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Labs home error: {e}")
        return HTMLResponse(content="<html><body>Error</body></html>", status_code=500)

@app.get("/webapp/labs/{lab_id}", response_class=HTMLResponse)
async def webapp_lab_detail(lab_id: int, token: str = ""):
    """Shows specific lab detail."""
    try:
        user_id, is_premium = verify_token(token)
        if not user_id: return HTMLResponse(content="Error: Sesión", status_code=403)
        if not is_premium: return HTMLResponse(content=f"<html><head><meta http-equiv='refresh' content='0;url=/webapp/upsell?token={token}'></head></html>", media_type="text/html; charset=utf-8")
        
        from labs_content import LABS, LAB_CATEGORIES
        
        if lab_id not in LABS:
            return HTMLResponse(content="Lab no encontrado", status_code=404)
            
        lab = LABS[lab_id]
        cat_name = LAB_CATEGORIES[lab['cat']]
        
        html = HTML_LAB_DETAIL.replace("{lab_id}", str(lab_id))\
            .replace("{title}", lab['title'])\
            .replace("{category}", cat_name)\
            .replace("{mission}", lab['mission'])\
            .replace("{command}", lab['command'])\
            .replace("{output}", lab['output'].replace('\\n', '\\\\n').replace('"', '\\"').replace("'", "\\'"))\
            .replace("{question}", lab['question'])\
            .replace("{token}", token)
            
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
        
    except Exception as e:
        logger.exception(f"Lab detail error: {e}")
        return HTMLResponse(content="<html><body>Error</body></html>", status_code=500)

@app.post("/api/labs/check")
async def api_labs_check(request: Request):
    try:
        data = await request.json()
        token = data.get('token')
        lab_id = data.get('lab_id')
        flag = data.get('flag')
        
        user_id, _ = verify_token(token)
        if not user_id: return JSONResponse({"success": False, "error": "Auth failed"})
        
        from labs_content import LABS
        from database_manager import mark_lab_completed, add_xp, get_user_completed_labs
        
        if lab_id not in LABS: return JSONResponse({"success": False, "error": "Lab not found"})
        
        lab = LABS[lab_id]
        
        # Check flag
        if flag.strip().lower() == lab['flag'].lower():
            # Check if already done
            completed = await get_user_completed_labs(user_id)
            if lab_id not in completed:
                await mark_lab_completed(user_id, lab_id)
                await add_xp(user_id, lab['xp'])
                
            return JSONResponse({"success": True, "xp": lab['xp']})
        else:
            return JSONResponse({"success": False})
            
    except Exception as e:
        logger.exception(f"Api lab check error: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/learning/get_content")
async def api_learning_get_content(request: Request):
    try:
        data = await request.json()
        token = data.get('token')
        module_id = int(data.get('module_id'))
        force = data.get('force', False)
        
        user_id, is_premium = verify_token(token)
        if not user_id: return JSONResponse({"success": False, "error": "Sesión expirada"})
        if not is_premium: return JSONResponse({"success": False, "error": "Requiere Premium"})
        
        from ai_learning import generate_lesson
        
        # Determine strict timeout/concurrency if needed
        html_content = await generate_lesson(module_id, force_refresh=force)
        
        return JSONResponse({"success": True, "html": html_content})
    except Exception as e:
        logger.exception(f"AI Content API error: {e}")
        return JSONResponse({"success": False, "error": "Error generando contenido"})

@app.get("/webapp/learning/complete_module/{module_id}")
async def webapp_learning_complete(module_id: int, token: str = ""):
    try:
        user_id, is_premium = verify_token(token)
        if not user_id: return JSONResponse({"ok": False, "error": "Auth failed"})
        if not is_premium: return JSONResponse({"ok": False, "error": "Premium required"})
        
        from database_manager import mark_module_completed, add_xp
        
        # Mark in DB
        result = await mark_module_completed(user_id, module_id)
        if result:
            await add_xp(user_id, 20)
            
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.exception(f"Error completing module: {e}")
        return JSONResponse({"ok": False, "error": str(e)})
