import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
IPN_SECRET_KEY = os.getenv("IPN_SECRET_KEY")

# Optional controls
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
GROQ_EMBEDDING_MODEL = os.getenv('GROQ_EMBEDDING_MODEL', 'embed-english-3.0')
# Embedding/backend controls
EMBEDDING_BACKEND = os.getenv('EMBEDDING_BACKEND', 'none')  # options: groq | openai | local | none
ENABLE_GROQ_CHAT = os.getenv('ENABLE_GROQ_CHAT', '1').strip() in ('1', 'true', 'True')
FALLBACK_AI_TEXT = os.getenv('FALLBACK_AI_TEXT', 'Lo siento, no puedo procesar tu pregunta en este momento. Inténtalo de nuevo más tarde.')
# No fallbacks by default - the single GROQ_MODEL is authoritative

DEFAULT_CREDITS_ON_REGISTER = int(os.getenv('DEFAULT_CREDITS_ON_REGISTER', '0'))
SKIP_ENV_VALIDATION = os.getenv('SKIP_ENV_VALIDATION', '0').strip() in ('1', 'true', 'True')
# When running in polling mode, set this to 1 if you want to have the bot delete any existing webhook
# automatically to avoid conflicting getUpdates vs webhook calls. Use with caution.
DELETE_WEBHOOK_ON_POLLING = os.getenv('DELETE_WEBHOOK_ON_POLLING', '0').strip() in ('1', 'true', 'True')

# Validación de variables críticas
def validate_config(require_all: bool = True):
    """Validate env vars. If SKIP_ENV_VALIDATION is set, do not raise.
    If require_all is False, only validate the core env vars for DB and Groq.
    """
    if SKIP_ENV_VALIDATION:
        return
    missing = []
    reqs = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "GROQ_API_KEY"] if not require_all else ["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_ANON_KEY", "GROQ_API_KEY", "NOWPAYMENTS_API_KEY", "IPN_SECRET_KEY"]
    for var in reqs:
        if globals().get(var) is None:
            missing.append(var)
    if missing:
        raise EnvironmentError(f"Faltan variables de entorno críticas: {', '.join(missing)}")

validate_config()
