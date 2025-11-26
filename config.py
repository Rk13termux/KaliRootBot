import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUMROAD_WEBHOOK_SECRET = os.getenv("GUMROAD_WEBHOOK_SECRET")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

# Optional controls
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
# No fallbacks by default - the single GROQ_MODEL is authoritative

DEFAULT_CREDITS_ON_REGISTER = int(os.getenv('DEFAULT_CREDITS_ON_REGISTER', '0'))
SKIP_ENV_VALIDATION = os.getenv('SKIP_ENV_VALIDATION', '0').strip() in ('1', 'true', 'True')

# Validación de variables críticas
def validate_config(require_all: bool = True):
    """Validate env vars. If SKIP_ENV_VALIDATION is set, do not raise.
    If require_all is False, only validate the core env vars for DB and Groq.
    """
    if SKIP_ENV_VALIDATION:
        return
    missing = []
    reqs = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "GROQ_API_KEY"] if not require_all else ["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_ANON_KEY", "GROQ_API_KEY", "GUMROAD_WEBHOOK_SECRET"]
    for var in reqs:
        if globals().get(var) is None:
            missing.append(var)
    if missing:
        raise EnvironmentError(f"Faltan variables de entorno críticas: {', '.join(missing)}")

validate_config()
