import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY)

async def get_user_learning(user_id: int) -> dict:
    """Obtiene el progreso de aprendizaje y nivel del usuario."""
    try:
        res = supabase.table("user_learning_levels").select("*").eq("user_id", str(user_id)).single().execute()
        if res.data:
            return res.data
        return {}
    except Exception as e:
        logger.exception(f"Error al obtener progreso de usuario {user_id}: {e}")
        return {}

async def add_experience(user_id: int, xp: int) -> dict:
    """Suma experiencia y gestiona subida de nivel."""
    try:
        user = await get_user_learning(user_id)
        if not user:
            # Si no existe, crear registro
            payload = {"user_id": str(user_id), "nivel": 1, "experiencia": xp, "lecciones_completadas": 0}
            supabase.table("user_learning_levels").insert(payload).execute()
            return payload
        nueva_xp = user["experiencia"] + xp
        nuevo_nivel = user["nivel"]
        # Ejemplo: cada 100 XP sube de nivel
        while nueva_xp >= 100:
            nueva_xp -= 100
            nuevo_nivel += 1
        update = {"experiencia": nueva_xp, "nivel": nuevo_nivel, "updated_at": "now()"}
        supabase.table("user_learning_levels").update(update).eq("user_id", str(user_id)).execute()
        return {**user, **update}
    except Exception as e:
        logger.exception(f"Error al sumar XP a usuario {user_id}: {e}")
        return {}

async def complete_lesson(user_id: int) -> dict:
    """Marca una lección como completada y suma XP."""
    try:
        user = await get_user_learning(user_id)
        if not user:
            await add_experience(user_id, 10)
            user = await get_user_learning(user_id)
        nuevas_lecciones = user["lecciones_completadas"] + 1
        supabase.table("user_learning_levels").update({"lecciones_completadas": nuevas_lecciones, "updated_at": "now()"}).eq("user_id", str(user_id)).execute()
        await add_experience(user_id, 10)  # Suma XP por lección
        return {**user, "lecciones_completadas": nuevas_lecciones}
    except Exception as e:
        logger.exception(f"Error al completar lección usuario {user_id}: {e}")
        return {}
