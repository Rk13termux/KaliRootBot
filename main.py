from fastapi import FastAPI, Request, HTTPException, Response
import socket
from contextlib import asynccontextmanager
import uvicorn
import logging

logging.basicConfig(level=logging.DEBUG)
import logging
import os
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from bot_logic import handle_message
from gumroad_handler import process_gumroad_webhook
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler('start', handle_message))
telegram_app.add_handler(CommandHandler('saldo', handle_message))
telegram_app.add_handler(CommandHandler('comprar', handle_message))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


logger = logging.getLogger(__name__)
TELEGRAM_STARTED = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the Telegram application so it can process enqueued updates
    try:
        # Ensure the telegram_app is initialized and started only once via lifespan
        await telegram_app.initialize()
        await telegram_app.start()
        global TELEGRAM_STARTED
        TELEGRAM_STARTED = True
        logger.info("Telegram application started via lifespan.")
        # If we have a TELEGRAM_WEBHOOK_URL set via env, attempt to set webhook for Telegram
        if TELEGRAM_WEBHOOK_URL:
            # Quick warning if the configured webhook URL lacks a path
            if TELEGRAM_WEBHOOK_URL.rstrip('/').endswith('onrender.com'):
                logger.warning('TELEGRAM_WEBHOOK_URL appears to be the root domain. Consider using the full webhook path: https://<your-domain>/webhook/telegram')
            try:
                logger.info('Setting Telegram webhook to %s', TELEGRAM_WEBHOOK_URL)
                # If a secret token is provided, register it with the webhook so Telegram
                # includes it in the `X-Telegram-Bot-Api-Secret-Token` header.
                if TELEGRAM_WEBHOOK_SECRET:
                    await telegram_app.bot.set_webhook(TELEGRAM_WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET)
                else:
                    await telegram_app.bot.set_webhook(TELEGRAM_WEBHOOK_URL)
                logger.info('Webhook set successfully')
            except Exception as e:
                logger.exception('Failed to set webhook: %s', e)
    except Exception:
        # If the Telegram initialization fails, the HTTP server will still run.
        pass
    try:
        yield
    finally:
        try:
            # If we set a webhook previously, delete it on shutdown to avoid stale webhooks
            if TELEGRAM_WEBHOOK_URL:
                try:
                    await telegram_app.bot.delete_webhook()
                    logger.info('Deleted Telegram webhook')
                except Exception as e:
                    logger.exception('Failed to delete Telegram webhook: %s', e)
            await telegram_app.stop()
            await telegram_app.shutdown()
            TELEGRAM_STARTED = False
            logger.info("Telegram application stopped via lifespan.")
        except Exception:
            pass
    # Signal handler: log termination reason if process receives SIGTERM/SIGINT
    try:
        import signal
        def _log_signal(sig, frame):
            logger.info('Process received signal %s; exiting', sig)
        signal.signal(signal.SIGTERM, _log_signal)
        signal.signal(signal.SIGINT, _log_signal)
    except Exception:
        logger.debug('Could not set signal handlers for logging')

app = FastAPI(lifespan=lifespan)

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    # Parse JSON body into a telegram.Update and push it to the PTB update queue
    body = await request.json()
    # Validate Telegram 'secret_token' header if configured
    telegram_secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token') or request.headers.get('X-Telegram-Bot-Api-Secret-Token'.lower())
    from config import TELEGRAM_WEBHOOK_SECRET
    if TELEGRAM_WEBHOOK_SECRET and (telegram_secret_header != TELEGRAM_WEBHOOK_SECRET):
        logger.warning('Rejected webhook request with invalid secret header')
        raise HTTPException(status_code=401, detail='Invalid webhook secret')
    try:
        update = Update.de_json(body, telegram_app.bot)
    except Exception:
        # If conversion fails, return a 400
        raise HTTPException(status_code=400, detail="Invalid Update payload")
    logger.debug(f"Received webhook update: {body}")
    await telegram_app.update_queue.put(update)
    return {"status": "ok"}

@app.post("/webhook/gumroad")
async def gumroad_webhook(request: Request):
    signature = request.headers.get("X-Gumroad-Signature", "")
    body = await request.body()
    result = await process_gumroad_webhook(body, signature)
    if result["status"] != 200:
        raise HTTPException(status_code=result["status"], detail=result["message"])
    return result


@app.get("/")
async def root():
    # basic service health endpoint
    return {"status": "ok", "service": "kali-tutor-bot"}


@app.head("/")
async def root_head() -> Response:
    """Explicit HEAD handler to satisfy some health checkers (e.g., Render) that send HEAD to '/'.

    Returning 200 avoids 405 Method Not Allowed and unexpected re-deploys from Render's health checks.
    """
    return Response(status_code=200)


@app.post('/debug/register')
async def debug_register(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        from database_manager import register_user_if_not_exists
        created = await register_user_if_not_exists(int(user_id), first_name=first_name, last_name=last_name, username=username)
        return {"status": "ok", "created": created}
    except Exception as e:
        logger.exception("debug_register error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/debug/register-raw')
async def debug_register_raw(request: Request):
    """Directly call supabase upsert and return raw response for debugging."""
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        from database_manager import supabase
        payload = {"user_id": int(user_id)}
        if 'first_name' in data and data['first_name'] is not None:
            payload['first_name'] = data['first_name']
        if 'last_name' in data and data['last_name'] is not None:
            payload['last_name'] = data['last_name']
        if 'username' in data and data['username'] is not None:
            payload['username'] = data['username']
        res = supabase.table('usuarios').upsert(payload).execute()
        # Build a safe response to show what happened
        result = {
            'data': getattr(res, 'data', None),
            'error': getattr(res, 'error', None),
            'status_code': getattr(res, 'status_code', None)
        }
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_register_raw error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/debug/register-rpc')
async def debug_register_rpc(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    initial_balance = data.get('initial_balance', 0)
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        from database_manager import supabase
        params = {"uid": int(user_id), "first_name": first_name, "last_name": last_name, "username": username, "initial_balance": int(initial_balance)}
        res = supabase.rpc('add_or_update_user', params).execute()
        result = {
            'data': getattr(res, 'data', None),
            'error': getattr(res, 'error', None),
            'status_code': getattr(res, 'status_code', None)
        }
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_register_rpc error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/debug/env')
async def debug_env():
    """Return presence (boolean) of critical environment variables; do not expose values."""
    import os
    checks = {
        'TELEGRAM_BOT_TOKEN_present': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
        'SUPABASE_URL_present': bool(os.getenv('SUPABASE_URL')),
        'SUPABASE_ANON_KEY_present': bool(os.getenv('SUPABASE_ANON_KEY')),
        'SUPABASE_SERVICE_KEY_present': bool(os.getenv('SUPABASE_SERVICE_KEY')),
        'GROQ_API_KEY_present': bool(os.getenv('GROQ_API_KEY')),
        'GUMROAD_WEBHOOK_SECRET_present': bool(os.getenv('GUMROAD_WEBHOOK_SECRET')),
    }
    return {'status': 'ok', 'env': checks}


@app.post('/debug/deduct')
async def debug_deduct(request: Request):
    """Attempt to call deduct_credit RPC for a user and return raw RPC response for debugging."""
    data = await request.json()
    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        from database_manager import supabase, get_user_credits
        before = await get_user_credits(int(user_id))
        res = supabase.rpc('deduct_credit', {'uid': int(user_id)}).execute()
        after = await get_user_credits(int(user_id))
        result = {
            'before': before,
            'raw_rpc': {
                'data': getattr(res, 'data', None),
                'error': getattr(res, 'error', None),
                'status_code': getattr(res, 'status_code', None),
            },
            'after': after
        }
        return {'status': 'ok', 'result': result}
    except Exception as e:
        logger.exception('debug_deduct error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/debug/db-check')
async def debug_db_check():
    try:
        from database_manager import test_connection
        ok = test_connection()
        return {"status": "ok", "db_ok": ok}
    except Exception as e:
        logger.exception("db-check error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/status')
async def status():
    return {
        'telegram_started': TELEGRAM_STARTED,
        'bot_service': 'kali-tutor-bot'
    }

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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    if not is_port_free(host, port):
        print(f"Port {port} appears to be in use. Trying higher ports up to {port+9}...")
        found = None
        for p in range(port + 1, port + 10):
            if is_port_free(host, p):
                found = p
                break
        if found is None:
            print(f"No free ports found in range {port+1} to {port+9}. Aborting.")
            exit(1)
        else:
            print(f"Using fallback port {found} instead of {port}.")
            port = found
    uvicorn.run("main:app", host=host, port=port)
