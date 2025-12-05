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
    <title>KaliRoot Elite</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #17212b);
            color: var(--tg-theme-text-color, #ffffff);
            min-height: 100vh;
            padding-bottom: 80px;
        }
        
        .header {
            background: var(--tg-theme-secondary-bg-color, #232e3c);
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
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding: 16px;
        }
        .stat-card {
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--tg-theme-button-color, #3390ec);
        }
        .stat-label {
            font-size: 11px;
            color: var(--tg-theme-hint-color, #708499);
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .section-title {
            padding: 20px 16px 12px;
            font-size: 13px;
            font-weight: 600;
            color: var(--tg-theme-hint-color, #708499);
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
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-radius: 12px;
            padding: 16px;
            text-decoration: none;
            color: inherit;
            transition: transform 0.2s, box-shadow 0.2s;
            display: block;
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
            color: var(--tg-theme-hint-color, #708499);
        }
        .resource-badge {
            display: inline-block;
            background: rgba(51, 144, 236, 0.2);
            color: var(--tg-theme-button-color, #3390ec);
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
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: inherit;
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
        .action-subtitle { font-size: 13px; color: var(--tg-theme-hint-color, #708499); }
        .action-arrow { color: var(--tg-theme-hint-color, #708499); font-size: 18px; }
        
        .bottom-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--tg-theme-secondary-bg-color, #232e3c);
            border-top: 1px solid rgba(255,255,255,0.05);
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
        }
        .bottom-btn.primary {
            background: var(--tg-theme-button-color, #3390ec);
            color: var(--tg-theme-button-text-color, #fff);
        }
        .bottom-btn.secondary {
            background: rgba(255,255,255,0.08);
            color: var(--tg-theme-text-color, #fff);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="avatar">{user_initial}</div>
        <div class="user-info">
            <h2>{user_name}</h2>
            <span class="badge">👑 ELITE MEMBER</span>
        </div>
    </div>
    
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
        <a href="#" class="action-item" onclick="goToBot('labs')">
            <div class="action-icon green">🧪</div>
            <div class="action-content">
                <div class="action-title">Laboratorios</div>
                <div class="action-subtitle">Practica en entornos reales</div>
            </div>
            <span class="action-arrow">›</span>
        </a>
        <a href="#" class="action-item" onclick="goToBot('learning')">
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
    
    <div class="bottom-bar">
        <button class="bottom-btn secondary" onclick="closeApp()">Cerrar</button>
        <button class="bottom-btn primary" onclick="goToBot('menu')">📱 Ir al Bot</button>
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
            .replace("{days_left}", str(days_left))
        
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
