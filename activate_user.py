import asyncio
from database_manager import supabase
import sys

async def activate_user_manual(user_id: int):
    print(f"🔄 Activando suscripción para usuario {user_id}...")
    try:
        # Calcular fecha de expiración (30 días)
        from datetime import datetime, timedelta
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        
        data = {
            "subscription_status": "active",
            "subscription_expiry_date": expiry
        }
        
        res = supabase.table("usuarios").update(data).eq("user_id", user_id).execute()
        
        if getattr(res, 'data', None):
            print(f"✅ ¡Éxito! El usuario {user_id} ahora es PREMIUM.")
            print(f"📅 Expira el: {expiry}")
        else:
            print("❌ Error: No se pudo actualizar. Verifica que el usuario exista.")
            
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        uid = int(sys.argv[1])
        asyncio.run(activate_user_manual(uid))
    else:
        print("Uso: python activate_user.py <USER_ID>")
