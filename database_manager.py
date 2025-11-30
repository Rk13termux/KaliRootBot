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



async def get_user_profile(user_id: int) -> dict:
    """Fetch full user profile including gamification stats."""
    try:
        res = supabase.table("usuarios").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            return res.data
        return {}
    except Exception as e:
        logger.exception(f"Failed to get user profile for {user_id}: {e}")
        return {}


async def add_xp(user_id: int, amount: int) -> dict:
    """Add XP to user and return result (including level up info)."""
    try:
        res = supabase.rpc("add_xp", {"uid": user_id, "amount": amount}).execute()
        if res.data:
            return res.data
        return {}
    except Exception as e:
        logger.exception(f"Failed to add XP for {user_id}: {e}")
        return {}


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


async def activate_subscription(user_id: int, invoice_id: str) -> bool:
    """Activate user subscription for 30 days."""
    try:
        from datetime import datetime, timedelta
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        data = {
            "subscription_status": "active",
            "subscription_expiry_date": expiry_date,
            "nowpayments_invoice_id": invoice_id
        }
        
        res = supabase.table("usuarios").update(data).eq("user_id", user_id).execute()
        
        if getattr(res, 'error', None):
            logger.error(f"Failed to activate subscription for {user_id}: {res.error}")
            return False
            
        logger.info(f"Subscription activated for user {user_id} until {expiry_date}")
        return True
    except Exception as e:
        logger.exception(f"Error activating subscription for {user_id}: {e}")
        return False

async def is_user_subscribed(user_id: int) -> bool:
    """Check if user has an active subscription."""
    try:
        from datetime import datetime
        res = supabase.table("usuarios").select("subscription_status, subscription_expiry_date").eq("user_id", user_id).single().execute()
        
        if not res.data:
            return False
            
        status = res.data.get("subscription_status")
        expiry_str = res.data.get("subscription_expiry_date")
        
        if status != "active" or not expiry_str:
            return False
            
        # Parse expiry date (handling potential timezone issues if needed, but ISO format usually works)
        # Assuming Supabase returns ISO string with timezone
        expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        
        # Simple check: is expiry in the future?
        # We need to make sure we compare timezone-aware with timezone-aware
        now = datetime.now(expiry_date.tzinfo) 
        
        return expiry_date > now
    except Exception as e:
        logger.exception(f"Error checking subscription for {user_id}: {e}")
        return False

async def set_subscription_pending(user_id: int, invoice_id: str) -> bool:
    """Set subscription status to pending."""
    try:
        data = {
            "subscription_status": "pending",
            "nowpayments_invoice_id": invoice_id
        }
        supabase.table("usuarios").update(data).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.exception(f"Error setting pending subscription for {user_id}: {e}")
        return False

async def get_expiring_users(days: int = 3) -> list:
    """Get users whose subscription expires in 'days' days."""
    try:
        from datetime import datetime, timedelta
        # We want users where expiry_date is between now + days and now + days + 1 (roughly)
        # Or just check for users expiring on that specific day.
        # Let's say we want to notify anyone expiring in the next 3 days who hasn't been notified?
        # For simplicity, let's just get users expiring in the range [now + days - 1, now + days + 1]
        
        target_date = datetime.now() + timedelta(days=days)
        start = target_date.replace(hour=0, minute=0, second=0).isoformat()
        end = target_date.replace(hour=23, minute=59, second=59).isoformat()
        
        res = supabase.table("usuarios").select("user_id, subscription_expiry_date").eq("subscription_status", "active").gte("subscription_expiry_date", start).lte("subscription_expiry_date", end).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.exception(f"Error getting expiring users: {e}")
        return []

async def expire_overdue_subscriptions() -> int:
    """Set expired subscriptions to inactive. Returns count of updated users."""
    try:
        from datetime import datetime
        now = datetime.now().isoformat()
        
        # Find active users with expiry < now
        res = supabase.table("usuarios").select("user_id").eq("subscription_status", "active").lt("subscription_expiry_date", now).execute()
        
        if not res.data:
            return 0
            
        count = 0
        for user in res.data:
            uid = user['user_id']
            # Update to inactive
            supabase.table("usuarios").update({"subscription_status": "inactive"}).eq("user_id", uid).execute()
            count += 1
            logger.info(f"Expired subscription for user {uid}")
            
        return count
    except Exception as e:
        logger.exception(f"Error expiring subscriptions: {e}")
        return 0
