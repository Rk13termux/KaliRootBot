from fastapi import FastAPI, Request, HTTPException, Response
import socket
from contextlib import asynccontextmanager
import uvicorn
import logging
import os
import json

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from bot_logic import handle_message
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
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler('start', handle_message))
telegram_app.add_handler(CommandHandler('saldo', handle_message))
telegram_app.add_handler(CommandHandler('comprar', handle_message))
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
