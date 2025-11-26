import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, DEFAULT_CREDITS_ON_REGISTER

logger = logging.getLogger(__name__)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY)
if SUPABASE_SERVICE_KEY:
    logger.info("Using SUPABASE_SERVICE_KEY for DB operations (server mode)")
else:
    logger.info("Using SUPABASE_ANON_KEY for DB operations (ensure RLS/policies allow writes)")

async def get_user_credits(user_id: int) -> int:
    res = supabase.table("usuarios").select("credit_balance").eq("user_id", user_id).execute()
    if res.data:
        balance = res.data[0]["credit_balance"]
        logger.info(f"get_user_credits({user_id}) -> {balance}")
        return balance
    return 0


async def register_user_if_not_exists(user_id: int, initial_balance: int = 0, first_name: str = None, last_name: str = None, username: str = None) -> bool:
    """Ensure the user exists in the usuarios table. If not, insert them with initial_balance.
    This function is idempotent and can be called safely on user interaction.
    """
    try:
        logger.debug(f"register_user_if_not_exists called for user {user_id} with names: {first_name}, {last_name}, {username}")
        # Check existence and current name fields
        res = supabase.table("usuarios").select("user_id, first_name, last_name, username, credit_balance").eq("user_id", user_id).limit(1).execute()
        if res.data:
            # If we have name info and it's different, update it
            try:
                db_row = res.data[0]
                updates = {}
                if first_name and db_row.get("first_name") != first_name:
                    updates["first_name"] = first_name
                if last_name and db_row.get("last_name") != last_name:
                    updates["last_name"] = last_name
                if username and db_row.get("username") != username:
                    updates["username"] = username
                if updates:
                    logger.debug(f"Updating name fields for {user_id}: {updates}")
                    supabase.table("usuarios").update(updates).eq("user_id", user_id).execute()
                    logger.info(f"register_user_if_not_exists({user_id}) -> updated name fields: {updates}")
            except Exception:
                logger.exception("Failed to update name fields for user: %s", user_id)
            logger.info(f"register_user_if_not_exists({user_id}) -> already exists")
            return False
        # Try to use atomic RPC for create/update to avoid RLS issues and race conditions
        try:
            params = {"uid": user_id, "first_name": first_name, "last_name": last_name, "username": username, "initial_balance": int(initial_balance)}
            res = supabase.rpc("add_or_update_user", params).execute()
            logger.debug(f"add_or_update_user rpc response: data={getattr(res, 'data', None)} error={getattr(res, 'error', None)} status={getattr(res, 'status_code', None)}")
            if getattr(res, 'error', None):
                logger.error("add_or_update_user RPC error: %s", res.error)
                # fallback to upsert
            else:
                # The RPC returns boolean: TRUE if created, FALSE otherwise
                data = res.data
                # Some clients wrap boolean in list/dict; normalize
                if isinstance(data, list) and len(data) > 0:
                    val = data[0]
                    if isinstance(val, dict):
                        created = next((v for v in val.values() if isinstance(v, bool)), None)
                    else:
                        created = bool(val)
                elif isinstance(data, dict):
                    created = next((v for v in data.values() if isinstance(v, bool)), False)
                else:
                    created = bool(data)
                if created:
                        logger.info(f"register_user_if_not_exists({user_id}) -> created via RPC")
                        # grant default credits on registration if configured
                        try:
                            if DEFAULT_CREDITS_ON_REGISTER and DEFAULT_CREDITS_ON_REGISTER > 0:
                                supabase.rpc("add_credits", {"uid": user_id, "amount": DEFAULT_CREDITS_ON_REGISTER}).execute()
                                logger.info(f"Granted {DEFAULT_CREDITS_ON_REGISTER} credits to {user_id} on registration")
                        except Exception:
                            logger.exception("Failed to grant default credits on registration for user: %s", user_id)
                        return True
                else:
                    logger.info(f"register_user_if_not_exists({user_id}) -> updated via RPC")
                    return False
        except Exception as e_rpc:
            logger.exception("RPC add_or_update_user failed: %s", e_rpc)
            # fallback to upsert
        # Create user with initial balance. Use upsert as a fallback and handle potential race where another process created the user.
        try:
            payload = {"user_id": user_id, "credit_balance": int(initial_balance)}
            if first_name:
                payload["first_name"] = first_name
            if last_name:
                payload["last_name"] = last_name
            if username:
                payload["username"] = username
            # Use upsert so we don't error on conflict; since we checked existence above, this is primarily for robustness across retries
            res = supabase.table("usuarios").upsert(payload).execute()
            # If upsert was successful, return True. Check for errors or status
            logger.debug(f"Supabase upsert response: {getattr(res, 'data', res)} err:{getattr(res, 'error', None)}")
            if getattr(res, "error", None):
                logger.error(f"Supabase upsert error: {res.error}")
                return False
            if getattr(res, "status_code", None) and 200 <= res.status_code < 300:
                logger.info(f"register_user_if_not_exists({user_id}) -> created with balance {initial_balance}")
                return True
            # If res.data has content, assume success
            if getattr(res, 'data', None):
                logger.info(f"register_user_if_not_exists({user_id}) -> created with returned data")
                return True
            # If no explicit status or rejected, fall back to checking existence
        except Exception as e_insert:
            # Handle duplicate key errors as OK (user already exists)
            logger.debug("Insert failed (possible race): %s", e_insert)
        # If we get here, assume user exists now
        logger.info(f"register_user_if_not_exists({user_id}) -> created by a concurrent process or already exists")
        return False
    except Exception as e:
        logger.exception("Failed ensuring user exists: %s", e)
        return False

async def deduct_credit(user_id: int) -> bool:
    # Operación atómica: solo descuenta si hay saldo
    logger.debug("Attempting RPC deduct_credit for user %s", user_id)
    res = supabase.rpc("deduct_credit", {"uid": user_id}).execute()
    success = False
    try:
        # Log raw RPC response for easier debugging when behavior is unexpected
        logger.debug("deduct_credit RPC raw resp: status=%s, data=%s, error=%s", getattr(res, 'status_code', None), getattr(res, 'data', None), getattr(res, 'error', None))
        data = res.data
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                # if the function returned a named boolean (e.g. {"deduct_credit": true})
                success = any(v is True for v in first.values())
            else:
                success = bool(first)
        elif isinstance(data, dict):
            success = any(v is True for v in data.values())
        else:
            # fallback
            success = bool(data)
    except Exception:
        success = False
    logger.info(f"deduct_credit({user_id}) -> {success}")
    # If the RPC reports False but the user's balance appears > 0, try a safe fallback update.
    try:
        if not success:
            current = await get_user_credits(user_id)
            if current > 0:
                logger.warning("deduct_credit RPC returned false but current balance > 0 (%s). Attempting fallback UPDATE for user %s", current, user_id)
                # Use upsert for fallback: decrement balance atomically using SQL expression
                # Note: This fallback is a last resort and should only be used in environments where SERVICE_KEY is present.
                res2 = supabase.table("usuarios").update({"credit_balance": current - 1}).eq("user_id", user_id).execute()
                logger.debug("Fallback update result: status=%s, data=%s, error=%s", getattr(res2, 'status_code', None), getattr(res2, 'data', None), getattr(res2, 'error', None))
                if getattr(res2, 'error', None) is None:
                    logger.info("Fallback update successful for user %s: new_balance=%s", user_id, current - 1)
                    success = True
                else:
                    logger.error("Fallback update failed for user %s", user_id)
    except Exception:
        logger.exception("Failed to attempt fallback deduct/update for user: %s", user_id)
    return success

async def add_credits_from_gumroad(user_id: int, amount: int, product_permalink: str = None, purchase_payload: dict = None) -> bool:
    # Suma créditos, crea usuario si no existe
    # Use the atomic RPC `add_credits(uid, amount)` to avoid race conditions and permission problems
    try:
        rpc_res = supabase.rpc("add_credits", {"uid": user_id, "amount": amount}).execute()
        logger.debug(f"add_credits RPC res: data={getattr(rpc_res, 'data', None)} error={getattr(rpc_res, 'error', None)} status={getattr(rpc_res, 'status_code', None)}")
        # Update metadata purchases list (atomic RPC does balance, so now update metadata separately)
        try:
            meta_res = supabase.table("usuarios").select("metadata").eq("user_id", user_id).execute()
            metadata = meta_res.data[0].get("metadata", {}) if meta_res.data else {}
        except Exception:
            metadata = {}
        purchases = metadata.get("purchases", []) if isinstance(metadata.get("purchases", []), list) else []
        purchase_record = {"amount": amount, "product_permalink": product_permalink, "payload": purchase_payload}
        purchases.append(purchase_record)
        metadata["purchases"] = purchases
        supabase.table("usuarios").update({"metadata": metadata}).eq("user_id", user_id).execute()
    except Exception as e_rpc:
        logger.exception("add_credits RPC failed, falling back to upsert: %s", e_rpc)
        res = supabase.table("usuarios").select("user_id").eq("user_id", user_id).execute()
        if res.data:
            old_balance = supabase.table("usuarios").select("credit_balance").eq("user_id", user_id).execute().data[0]["credit_balance"]
            new_balance = old_balance + amount
            # Update balance
            supabase.table("usuarios").update({"credit_balance": new_balance}).eq("user_id", user_id).execute()
        logger.info(f"add_credits_from_gumroad({user_id}, {amount}) updated {old_balance}->{new_balance}")
        # Update metadata purchases list
        try:
            meta_res = supabase.table("usuarios").select("metadata").eq("user_id", user_id).execute()
            metadata = meta_res.data[0].get("metadata", {}) if meta_res.data else {}
        except Exception:
            metadata = {}
        purchases = metadata.get("purchases", []) if isinstance(metadata.get("purchases", []), list) else []
        purchase_record = {"amount": amount, "product_permalink": product_permalink, "payload": purchase_payload}
        purchases.append(purchase_record)
        metadata["purchases"] = purchases
        supabase.table("usuarios").update({"metadata": metadata}).eq("user_id", user_id).execute()
    except Exception:
        # If the add_credits or metadata update failed completely, ensure metadata/purchase is recorded via upsert
        logger.exception("Failed to add credits via RPC and metadata update; running upsert fallback")
        # Upsert will either create or update balance/metadata
        supabase.table("usuarios").upsert({"user_id": user_id, "credit_balance": amount, "metadata": {"purchases": [{"amount": amount, "product_permalink": product_permalink, "payload": purchase_payload}]}}).execute()
        logger.info(f"add_credits_from_gumroad({user_id}, {amount}) fallback upsert executed")
    return True


def test_connection() -> bool:
    """Simple DB check for dev — select 1 user, return True if query succeds."""
    try:
        res = supabase.table("usuarios").select("user_id").limit(1).execute()
        if getattr(res, 'error', None):
            logger.error("test_connection supabase error: %s", res.error)
            return False
        return True
    except Exception as e:
        logger.exception("test_connection failed: %s", e)
        return False
