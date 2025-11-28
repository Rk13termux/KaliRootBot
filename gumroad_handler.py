import hmac
import hashlib
import json
from config import GUMROAD_WEBHOOK_SECRET
from database_manager import add_credits_from_gumroad

async def process_gumroad_webhook(request_body: bytes, signature_header: str) -> dict:
    # Validar firma HMAC-SHA256
    expected_sig = hmac.new(GUMROAD_WEBHOOK_SECRET.encode(), request_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature_header):
        return {"status": 401, "message": "Unauthorized"}
    try:
        payload = json.loads(request_body)
        event_type = payload.get("event")
        product_permalink = payload.get("product_permalink", "")
        # Extraer cantidad de créditos del permalink
        try:
            amount = int(product_permalink.split("-")[1])
        except Exception:
            amount = 0
        custom_fields = payload.get("custom_fields", {})
        telegram_user_id = int(custom_fields.get("telegram_user_id", 0))
        if telegram_user_id and amount:
            await add_credits_from_gumroad(telegram_user_id, amount, product_permalink=product_permalink, purchase_payload=payload)
            return {"status": 200, "message": f"Créditos añadidos: {amount} para usuario {telegram_user_id}"}
        else:
            return {"status": 400, "message": "Datos insuficientes en el webhook"}
    except Exception as e:
        return {"status": 500, "message": f"Error procesando webhook: {str(e)}"}
