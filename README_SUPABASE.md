### 👇 7) Deploying to Render (webhook mode for production)
 - `TELEGRAM_WEBHOOK_URL` — The public URL that Telegram will POST updates to. For Render, this is typically `https://<your-service>.onrender.com/webhook/telegram`.
 - Set the start command to run the FastAPI app (the main entrypoint uses uvicorn by default).
Start command example:
```bash
 uvicorn main:app --host 0.0.0.0 --port $PORT
```
 - Environment variables to configure in Render:
 - `TELEGRAM_BOT_TOKEN` — your Telegram Bot Token
 - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` — your Supabase keys
 - `GROQ_API_KEY`, `GROQ_MODEL`
 - `GUMROAD_WEBHOOK_SECRET`
 - `TELEGRAM_WEBHOOK_URL` — `https://<your-render-service>.onrender.com/webhook/telegram` (optional). If set, `main.py` will attempt to set the webhook automatically on startup.
 - `TELEGRAM_WEBHOOK_URL` — `https://<your-render-service>.onrender.com/webhook/telegram` (optional). If set, `main.py` will attempt to set the webhook automatically on startup.
 - `TELEGRAM_WEBHOOK_SECRET` — Optional: a random secret token you can configure so Telegram includes `X-Telegram-Bot-Api-Secret-Token` header in webhook callbacks; `main.py` will validate it.
 - Check logs in Render to ensure `telegram_app` started and that the webhook was set successfully (you should see a log message like `Webhook set successfully`).

Step-by-step (Render Web Service):

1) Create a new Web Service in Render and link your Git repository.
2) Choose the branch you want to deploy (e.g., `main`).
3) In the "Build & Deploy" options, set the build command to:
```bash
pip install -r requirements.txt
```
4) Set the start/Command to:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
5) Add the required environment variables in the `Environment` tab (TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, GROQ_API_KEY, GUMROAD_WEBHOOK_SECRET, GROQ_MODEL, and optionally TELEGRAM_WEBHOOK_URL). The `TELEGRAM_WEBHOOK_URL` should point to `https://<your-service>.onrender.com/webhook/telegram`.
6) Optionally configure a `Health Check` of `/status` and `PORT` as Render default.
7) Deploy. When Render finishes building and your app starts, verify the logs and visit the `/status` endpoint to check the bot is ready. If `TELEGRAM_WEBHOOK_URL` was configured, check `getWebhookInfo` to confirm Telegram is posting to the right endpoint.

If you prefer the app to handle setting the webhook automatically, make sure your `TELEGRAM_WEBHOOK_URL` env var is the exact public URL for webhook. The app will attempt to set it on startup and delete it on shutdown.
4) Verify the webhook is set (optional):
```bash
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo" | jq
```

To set the webhook manually with a secret token from your machine:

```bash
# Replace your token, url and secret token
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<your-service>.onrender.com/webhook/telegram&secret_token=<YOUR_SECRET>" | jq
```
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_SERVICE_KEY="your-service-role-key"  # optional but recommended for server-side write operations
-- Table: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
  user_id BIGINT PRIMARY KEY,
  credit_balance INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  username TEXT,
  first_name TEXT,
  last_name TEXT,
  metadata JSONB DEFAULT '{}'
);
# Supabase Migration & Population Scripts for `bot_service`

Este documento describe cómo usar los archivos incluidos para crear las tablas y poblar la base de conocimiento con contenido educativo con un "toque hacker / Kali Linux" orientado a la ética.

> ⚠️ Importante: los ejemplos y el contenido están orientados a educación, pruebas en laboratorio y buenas prácticas. No se proveen pasos para actividades maliciosas o ilegales. Mantén siempre el consentimiento y permiso para cualquier prueba.

## Requisitos previos

- Una instancia Supabase con acceso para ejecutar queries en SQL (console). Asegúrate de que la extensión `vector` esté activada (pgvector) y que `pgcrypto` esté disponible. La migración incluye crear ambas extensiones si tu rol lo permite.
- Variables de entorno en `.env` (o en el entorno de despliegue) para conectarte desde local:
  ### Resolver errores de importación en VSCode (Pylance)

  Si en VSCode ves mensajes como "No se ha podido resolver la importación 'supabase'", asegúrate de activar tu entorno virtual y de instalar las dependencias:

  ```bash
  python -m venv venv
  source venv/bin/activate
La variable `GROQ_MODEL` controla el modelo que se usará tanto para embeddings como para chat (por defecto). Mantén esta variable y evita separar los modelos para reducir complejidad.
  ```

  En VSCode, selecciona el intérprete Python correcto (el del virtualenv `venv`) para que Pylance use las dependencias instaladas en ese entorno.
  Si después de esto sigues viendo el error `No se ha podido resolver la importación "supabase"` o `groq`, ejecuta el script de verificación:

  ```bash
  python check_deps.py
  ```

  Si sigues viendo el error en Pylance **después** de seleccionar el intérprete, prueba lo siguiente:

  1) Ejecuta `pip show supabase groq` desde el terminal con el `venv` activado para confirmar que están instalados.
  2) En VSCode, abre la paleta (Cmd/Ctrl+Shift+P) y selecciona `Developer: Reload Window` para recargar el servidor del lenguaje.
  3) Finalmente, si deseas silenciar el aviso de Pylance temporalmente, abre `settings.json` y añade:

  ```json
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none"
  }
  ```

  Sin embargo, no es la recomendación preferida: es mejor configurar el interprete del venv.
  ### Script de desarrollo (crea venv y instala dependencias)

  He añadido un script `dev_setup.sh` para crear el virtualenv e instalar dependencias:

  ```bash
  ./dev_setup.sh
  # después, activa el venv en tu shell
  source venv/bin/activate
  ```

  El script también ejecuta `check_deps.py` para validar dependencias. Si ves avisos de Pylance en VSCode, selecciona el intérprete del venv.

  El script recomendará comandos para instalar paquetes faltantes y consejos para configurar el intérprete de VSCode.
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `GROQ_API_KEY`
  - `GUMROAD_WEBHOOK_SECRET`

## 1) Ejecutar migración SQL

Puedes ejecutar `supabase_migrations.sql` directamente desde el SQL Editor de Supabase o con `psql` si tienes acceso.

- En la consola de Supabase SQL, pega el contenido de `supabase_migrations.sql` y ejecútalo.
```bash
# si tienes las variables de entorno exportadas
psql "$SUPABASE_URL" -c "\i supabase_migrations.sql"
``` 

(Nota: `psql` no se conecta fácilmente con la URL de Supabase; es más práctico usar el SQL editor de Supabase o construir un cliente psql con host, puerto, user y password.)

## 2) Poblar la base con ejemplos (script Python)

El script `populate_knowledge_base.py` insertará entradas de ejemplo en la tabla `knowledge_base` usando embeddings calculados por la API de Groq.

Instala dependencias (recomendado en un virtualenv):
`GROQ_MODEL` — modelo Groq a usar por defecto para embeddings y chat.
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Ejecuta el script en modo `preview` (por defecto) para ver los payloads:

```bash
python populate_knowledge_base.py --preview
```

Ejecuta el script para insertar los registros en Supabase:

```bash
# Asegúrate de exportar las variables de entorno
export SUPABASE_URL="https://..."
export SUPABASE_ANON_KEY="eyJ..."
python populate_knowledge_base.py --insert
```

### Añadir saldo a usuarios (seed)

Para probar la funcionalidad de crédito y la IA, puedes añadir saldo a usuarios en la tabla `usuarios` de Supabase. Hay dos maneras:

1) Añadir (sumar) créditos usando la función RPC `add_credits(uid, amount)`:

```bash
# Añadir 5 créditos al usuario 12345
python seed_users.py --add --user 12345 --amount 5
```

2) Fijar (set) el saldo de forma absoluta (upsert):

```bash
# Fijar el balance del usuario 12345 en 10 créditos
python seed_users.py --set --user 12345 --amount 10
```

También puedes cargar un JSON con varios usuarios:

```json
[
  {"user_id": 12345, "amount": 10},
  {"user_id": 67890, "amount": 20}
]
```

```bash
# Cargar varios usuarios y añadir créditos
python seed_users.py --file users.json
```

Recuerda que `seed_users.py` usa la función RPC `add_credits` para la opción `--add`, que hace una suma atómica (si existe la función en tu DB). Para `--set` emplea un `upsert` que fija el saldo.

### Créditos al registrarse

Puedes configurar el bot para que otorgue automáticamente créditos cuando un usuario se registre (comando `/start`). Para hacerlo, define en tu `.env` la variable:

```bash
DEFAULT_CREDITS_ON_REGISTER=5
```

Si `DEFAULT_CREDITS_ON_REGISTER` es mayor que 0, el bot agregará esa cantidad de créditos al usuario la primera vez que ejecute `/start`.

### Comandos útiles del bot

- `/start` — Registrarse y recibir un mensaje de bienvenida. Si está configurado, te puede asignar créditos iniciales.
- `/saldo` — Consultar saldo actual de créditos.
- `/comprar` — Te enviará un enlace de Gumroad para comprar créditos.

### Modelos y embeddings (Groq)

Este proyecto usa exclusivamente modelos Groq. Para simplicidad, el bot, por defecto, utiliza una única variable `GROQ_MODEL` para ambos `chat` y `embeddings`. No se recomienda usar modelos diferentes para embed/chat en este proyecto: Mantén la configuración con `GROQ_MODEL`.

Ejemplo en `.env`:

```dotenv
GROQ_MODEL="llama-3.1-8b-instant"
```

La variable `GROQ_MODEL` controla el modelo que se usará tanto para embeddings como para chat (por defecto). Mantén la configuración con `GROQ_MODEL` para simplicidad y consistencia.

Si cambias el modelo a uno que devuelva embeddings con una dimensión distinta, asegúrate de que la columna `content_embedding` de la base de datos esté configurada con la dimensión correcta (p. ej. `VECTOR(384)`), y en caso contrario realiza la migración y recalculado de embeddings.

### Troubleshooting & Quick checks (Groq models)

1) Choose a Groq model (ensure it supports both embeddings and chat):

```bash
source venv/bin/activate
# Edit your .env and set GROQ_MODEL appropriately
```

2) If your `GROQ_MODEL` returns 404 or `model_decommissioned`, update `.env` with a model from your account and restart the bot.


### Consultar información del usuario

Puedes consultar el nombre y el usuario guardados en la tabla `usuarios` así:

```sql
SELECT user_id, username, first_name, last_name, credit_balance FROM usuarios WHERE user_id = 12345;
```

### Probar endpoints HTTP localmente

Una vez corriendo `python main.py` (uvicorn), puedes probar estos endpoints con curl:


```bash
curl -s http://127.0.0.1:8000/

Debug endpoints available in dev:

```bash
# Register a user directly with names (POST)
curl -X POST -H "Content-Type: application/json" -d '{"user_id":12345, "first_name":"Juan", "last_name":"Perez", "username":"juanperez"}' http://127.0.0.1:8000/debug/register

# Quick DB connectivity check (GET)
curl -s http://127.0.0.1:8000/debug/db-check | jq

Tip: Si al hacer insert/upsert recibes errores de permisos al usar la `SUPABASE_ANON_KEY`, añade `SUPABASE_SERVICE_KEY` (service_role key) para operaciones de servidor que necesitan permisos de escritura/actualización.
Evita exponer la `SUPABASE_SERVICE_KEY` en clientes o repositorios públicos.

## Producción — Recomendaciones de seguridad y RPC

Para producción recomendamos:

- Usar la RPC `add_or_update_user(uid, first_name, last_name, username, initial_balance)` desde el backend en vez de permitir `anon` insertar directamente en la tabla `usuarios`.
- Ejecutar el servidor con la variable de entorno `SUPABASE_SERVICE_KEY` (service_role key) para que el backend tenga permisos suficientes y no dependa de políticas abiertas en RLS.
- Configurar RLS en Supabase para evitar que `anon` tenga permisos de escritura en la tabla. Un ejemplo de política (permitir sólo SELECT a `anon`):

```sql
-- Permitir SELECT a 'anon'
DROP POLICY IF EXISTS allow_anon_select_usuarios ON usuarios;
CREATE POLICY allow_anon_select_usuarios ON usuarios
  FOR SELECT
  USING (true);
-- Denegar inserciones/actualizaciones desde anon.
```
## Debugging RPCs & auditing

If you see strange behavior where `get_user_credits` returns a positive balance but `deduct_credit` returns `false` (no deduction performed), follow these steps:

1) Use the server-side debug endpoint to call `deduct_credit` and view raw response:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"user_id": 12345}' http://127.0.0.1:8000/debug/deduct | jq
```

2) Alternatively, run the local debugging helper (requires `SUPABASE_SERVICE_KEY`) to see balance before/after and the raw RPC response:

```bash
python rpc_debug.py --user 12345
```

3) Note that `deduct_credit` is declared in the migration with `SECURITY DEFINER` and it now logs an audit event (`deduct_credit`) into the `audit_log` table showing the old and new balance. Make sure to re-apply the migration if you changed the function implementation after the initial migration.

4) If RLS policies are active and you do not use `SUPABASE_SERVICE_KEY`, RPCs that modify data should be `SECURITY DEFINER` functions or use a service role key. Confirm the `POST /debug/env` endpoint shows `SUPABASE_SERVICE_KEY_present: true`.


Si quieres permitir que clientes autenticados (con supabase-auth) inserten/actualicen sólo su propia fila, crea una columna `auth_user_id UUID` y genera políticas que comparen `auth.uid()` con dicho campo (no compares `auth.uid()` con `user_id` que es bigint — causa errores de cast).

Ejemplo de función RPC segura (ya creada en `supabase_migrations.sql`):
```sql
-- add_or_update_user(uid bigint, first_name text, last_name text, username text, initial_balance int)
-- Returns boolean: true if created, false if updated
SELECT * FROM add_or_update_user(12345, 'Juan', 'Perez', 'juanperez', 0);
```

Usar la RPC desde el servidor evita exponer permisos a usuarios finales y permite mantener políticas RLS estrictas.
```
```
### Running the bot locally with polling (recommended for dev)

If you'd rather run the bot via Polling than deploying a webhook, use the `run_polling.py` script. It's useful in development since it doesn't require a public webhook URL.

```bash
# Make sure venv is active
source venv/bin/activate
python run_polling.py
# Or with make
make poll
```

While the polling script is running, open your Telegram chat with the bot and send messages to test the bot's responses.

### Verificar el token de Telegram (recomendado)

Si recibes un error como "InvalidToken: The token `your-telegram-bot-token-here` was rejected by the server.", tu `TELEGRAM_BOT_TOKEN` está mal configurado.

Verifica rápidamente con curl (reemplaza `<YOUR_TOKEN>`):

```bash
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getMe" | jq
```

O usando el script suministrado:

```bash
python check_telegram_token.py <YOUR_TOKEN>
# o si ya exportaste TELEGRAM_BOT_TOKEN
python check_telegram_token.py
```

Si `getMe` falla con 404 o `ok: false`, revisa que el token sea el correcto, que no haya espacios, y que no sea un token de prueba mal copiado. Si usas `.env`, actualiza el valor y reinicia el proceso.


- Enviar un Update de Telegram (ejemplo de payload):

```bash
cat <<'JSON' > update.json
{
  "update_id": 10000,
  "message": {
    "message_id": 1,
    "from": {"id": 12345, "is_bot": false, "first_name": "Test"},
    "chat": {"id": 12345, "first_name": "Test", "type": "private"},
    "date": 1609459200,
    "text": "Hola"
  }
}
JSON

curl -X POST -H "Content-Type: application/json" -d @update.json http://127.0.0.1:8000/webhook/telegram
```

- Enviar un Webhook de Gumroad (firma HMAC-SHA256):

```bash
BODY='{"event": "sale", "product_permalink": "pack-100-creditos", "custom_fields": {"telegram_user_id": "12345"}}'
SIG=$(python - <<PY
import hmac, hashlib
secret=b"your_gumroad_secret"
print(hmac.new(secret, b'"$BODY"', hashlib.sha256).hexdigest())
PY
)

curl -X POST -H "Content-Type: application/json" -H "X-Gumroad-Signature: $SIG" -d "$BODY" http://127.0.0.1:8000/webhook/gumroad
```

Los pagos procesados por el webhook se guardan en el campo JSON `metadata` de la tabla `usuarios`. En particular, cada compra se añade en el array `metadata->purchases` para auditoría y trazabilidad.

Nota: la firma del ejemplo puede variar según el formato del `body` y la codificación; ajusta `your_gumroad_secret` y el `BODY`.

### Si obtienes "address already in use"

Si al arrancar el servidor ves este error:

```
ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

Prueba lo siguiente:

1) Averigua qué proceso está usando el puerto 8000:

```bash
lsof -i :8000
# o alternativamente
ss -ltnp | grep :8000
# o con netstat
sudo netstat -tulpn | grep :8000
```

2) Si el proceso es una instancia antigua del servidor o de uvicorn, deténlo (reemplaza <PID>):

```bash
kill <PID>
# si hace falta forzar
kill -9 <PID>
```

3) Si prefieres no matar procesos, ejecuta la app en otro puerto:

```bash
PORT=8001 python main.py
```

4) Alternativa: mata cualquier proceso uvicorn en ejecución (solo para desarrollo):

```bash
pkill -f uvicorn
```

Nota: `main.py` ahora intenta automáticamente elegir un puerto superior si 8000 está en uso (intenta 8001..8009). Si no se encuentra un puerto libre, el proceso se abortará con un mensaje.

### Usar Groq como proveedor de embeddings (sin torch)

Este proyecto está configurado por defecto para usar Groq como proveedor de embeddings y de completado, lo que evita la necesidad de instalar dependencias pesadas localmente (por ejemplo `torch`). Esto simplifica el desarrollo local y el despliegue en Render.

Variables necesarias para usar Groq:
- `GROQ_API_KEY` — clave para Groq (requerida)
 - `GROQ_MODEL` — modelo Groq a usar por defecto para embeddings y chat.

Prueba local para comprobar que el pipeline funciona con Groq (evita instalar torch en local):

```bash
export SKIP_ENV_VALIDATION=1
export GROQ_API_KEY="your-groq-api-key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
python run_local_test.py -q "¿Qué es Kali Linux?"
```

Si por alguna razón deseas investigar el uso de embeddings locales, puedes instalar dependencias adicionales manualmente; no es necesario para usar Groq.

Si recibes un error como "The model `embed-english-3.6` does not exist or you do not have access to it", revisa lo siguiente:

1. Verifica que `GROQ_API_KEY` sea válido y tenga permisos para el modelo que estás solicitando.
2. Entra a tu dashboard de Groq y verifica la lista de modelos disponibles (y sus nombres).
3. Actualiza `.env` con `GROQ_MODEL` a un modelo válido que tu cuenta Groq tenga disponible.

Por ejemplo:
```bash
export GROQ_MODEL="llama-3.1-8b-instant"
```

Si por alguna razón no quieres usar Groq o no tienes acceso, la app ahora maneja estos errores y usará contexto reciente de la `knowledge_base` (si existe) o devolverá un mensaje amigable indicando que la IA no está disponible.

### ¿No tienes un archivo `.env`?

Si no tienes un archivo `.env`, puedes crear uno fácilmente copiando el archivo de ejemplo y luego editándolo:

```bash
cp .env.example .env
# Edita el archivo y coloca tus valores reales (reemplaza los mensajes de ejemplo):
# nano .env

# O usa comandos sed para reemplazar (ajusta según sistema shell):
sed -i 's|AQUI_VA_EL_TOKEN|your-telegram-token|' .env
sed -i 's|AQUI_VA_LA_URL|https://your-project.supabase.co|' .env
sed -i 's|AQUI_VA_LA_ANON_KEY|your-anon-key|' .env
sed -i 's|AQUI_VA_LA_API_KEY|your-groq-api-key|' .env
sed -i 's|AQUI_VA_EL_SECRETO|your-gumroad-secret|' .env

# Comprobación rápida si las variables están presentes (no muestres los valores reales en logs):
grep -E "TELEGRAM_BOT_TOKEN|SUPABASE_URL|SUPABASE_ANON_KEY|GROQ_API_KEY|GUMROAD_WEBHOOK_SECRET" .env
```

Recuerda no compartir ni subir `.env` a repositorios públicos; usa `gitignore` para evitarlo.

Si te preocupa el consumo de tokens o memoria durante el encoding, puedes reducir el número de textos o particionarlos.

## 3) Uso de `search_knowledge_base` (RPC)

La función `search_knowledge_base(query_embedding float8[], top_k INTEGER DEFAULT 5)` es callable desde Supabase RPC. Un ejemplo en SQL (pasa vector como arreglo):

```sql
-- Supongamos que ya tienes una embedding 'arr' de tipo float8[]
SELECT * FROM search_knowledge_base(ARRAY[0.0001, 0.234, ...], 5);
```

Con `supabase-py`, puedes usar RPC con algo similar a:

```py
res = supabase.rpc('search_knowledge_base', {
    'query_embedding': embedding_list,
    'top_k': 5
}).execute()
```

## 4) Funciones de créditos

- `deduct_credit(user_id)` devuelve booleano y realiza decremento atómico. El RPC está definida en la migración SQL.
- `add_credits(user_id, amount)` añade créditos o crea el usuario si no existía.

### Registro automático de usuarios

Los usuarios se registran automáticamente la primera vez que usan el comando `/start` y se guarda su información básica (nombre y usuario). Esto sucede en `bot_logic.handle_message` cuando el usuario envía `/start`; la llamada a `database_manager.register_user_if_not_exists(user_id, first_name, last_name, username)` crea el registro en la tabla `usuarios` si no existe, y además actualiza los campos `first_name`, `last_name` y `username` si cambian.

También puedes crear o inicializar manualmente usuarios a través de `seed_users.py` si necesitas preparar balances para pruebas.

> Tip: Añade roles y políticas RLS a tu base si necesitas controlar acceso para RPCs desde clientes web.

## 5) Ajustes y personalización

- Cambia el estilo de contenido en `populate_knowledge_base.py` para añadir más entradas o adaptar el tono. Las entradas aquí son seguras y enfocadas a aprendizaje y buenas prácticas.
- Si usas otro modelo de embeddings cambia la dimensión vectorial en `supabase_migrations.sql` (aquí: 384 para `all-MiniLM-L6-v2`).

## 6) Notas de seguridad y ética

- No uses la base de conocimiento para instrucción de actividades maliciosas.
- Mantén registros de consentimiento y alcance en tus laboratorios.
- Si tu bot responde con voz de 'hacker', evita reproducir o justificar prácticas ilegales, y proporciona alternativas de aprendizaje y mitigación.

### ⚠️ Seguridad: protege tus claves y rotación de secretos

- Nunca comites ficheros con claves reales (.env o similares) a repositorios públicos. Usa siempre `.env.example` como plantilla con placeholders.
- Si accidentalmente subiste una clave secreta, **rota** (revoca) la clave inmediatamente desde el proveedor (Groq, Supabase, Telegram) y crea una nueva.
- Limpia el historial Git para eliminar la clave con una herramienta como `git-filter-repo` o BFG. Ejemplo con `git-filter-repo`:

```bash
# Instala git-filter-repo (si no lo tienes). Si usas Debian/Ubuntu:
pip install git-filter-repo

# Quita un archivo sensible (como .env) de todo el historial:
git filter-repo --path .env --invert-paths

# O limpia por clave concreta (ejemplo):
git filter-repo --replace-text <(printf "<YOUR_OLD_GROQ_KEY>==>REDACTED\n")

# Después de limpiar el historial, fuerza el push y reemplaza la rama remota:
git push --force origin main
```

- Otra alternativa es usar `bfg-repo-cleaner`: https://rtyley.github.io/bfg-repo-cleaner/
- Finalmente, actualiza las variables en tu entorno (Render, Docker, CI, Netlify, etc.) con las claves rotadas.

**Tips preventivos:**
- Añade `.env` a tu `.gitignore` (ya incluido) y no guardes ficheros con claves en el repo.
- Añade hooks de `pre-commit` que detecten secretos: por ejemplo, `pre-commit` combinado con `detect-secrets` o `git-secrets` puede bloquear commits que contienen API keys.

Ejemplo básico con `pre-commit` y `detect-secrets`:

```bash
pip install pre-commit detect-secrets
detect-secrets scan > .secrets.baseline
pre-commit install
```

#### GitHub / CI secrets & pre-merge scanning

- Use GitHub Secrets to store the real values for `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`, `GUMROAD_WEBHOOK_SECRET`, and other production secrets. Go to `Settings -> Secrets and variables -> Actions`.
- In CI or in Render deployments, reference those secrets instead of committing them to the repo.
- The repository includes a `.github/workflows/secret-scan.yml` job that runs `gitleaks` on push and PRs to detect accidental secrets and block merges if configured.

Quick steps to add GitHub secrets:

1) On GitHub repo: Settings > Secrets and variables > Actions > New repository secret
2) Add `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `SUPABASE_SERVICE_KEY`, `GUMROAD_WEBHOOK_SECRET`, etc.
3) Use these secrets in your GitHub Actions or in the deploy service configuration.

If the repo has sensitive keys tracked in history, follow the history-cleaning steps above and rotate the keys on the provider side.

Con esto, los commits serán validados y el hook puedes combinarlos en CI.

### Nota: no necesitas `torch` para usar este proyecto

Este proyecto está diseñado para usar la API de Groq para embeddings y completados, por lo que no es necesario instalar `torch` ni otros paquetes pesados para las funcionalidades principales.

Esto permite arrancar el bot localmente y hacer pruebas sin grandes blobs binarios que requieren GPU o instalaciones pesadas.

---

Si quieres, ahora puedo:
- Añadir más entradas educativas enfocadas en hardening, red teaming responsable, o análisis forense.
- Generar scripts para borrar/actualizar entradas.
- Añadir políticas RLS y roles en la migración para restringir acceso RPC.
