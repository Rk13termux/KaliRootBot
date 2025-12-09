import os
import re
import html
from typing import List
from groq import Groq
from groq import BadRequestError, NotFoundError
import logging
from supabase import create_client, Client
# import config variables
from config import SUPABASE_URL, SUPABASE_ANON_KEY, GROQ_API_KEY, GROQ_MODEL, GROQ_EMBEDDING_MODEL, EMBEDDING_BACKEND, ENABLE_GROQ_CHAT, FALLBACK_AI_TEXT
# (BadRequestError imported above)

logger = logging.getLogger(__name__)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
# Initialise groq client if API key present
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def select_first_available_embedding_model() -> str | None:
    """List available models via Groq and select a model that seems to support embeddings.

    Heuristic: prefer models with 'embed' in the model id; falls back to None.
    """
    try:
        if not groq_client:
            return None
        model_list = groq_client.models.list()  # type: ignore[attr-defined]
        if hasattr(model_list, 'data') and model_list.data:
            for m in model_list.data:
                mid = getattr(m, 'id', None) or m.get('id') if isinstance(m, dict) else None
                if not mid:
                    continue
                if 'embed' in mid.lower():
                    logger.info('Auto-selected embedding model %s from account models', mid)
                    return mid
            # No 'embed' in names, fall back to first model if any
            if len(model_list.data) > 0:
                first = model_list.data[0]
                mid = getattr(first, 'id', None) or first.get('id') if isinstance(first, dict) else None
                logger.info('No explicit embedding model found; selecting first model %s', mid)
                return mid
    except Exception:
        logger.debug('Could not list Groq models; perhaps the API key is invalid or network failure')
    return None

logger.info('Using Groq MODEL for chat & embed: %s', GROQ_MODEL)

async def get_ai_response(user_id: int, query: str) -> str:
    logger.debug('get_ai_response called; EMBEDDING_BACKEND=%s ENABLE_GROQ_CHAT=%s', EMBEDDING_BACKEND, ENABLE_GROQ_CHAT)
    
    # 0. Recuperar Historial de Chat (Memoria)
    from database_manager import get_chat_history, save_chat_interaction
    chat_history = await get_chat_history(user_id, limit=8) # Últimos 8 mensajes (4 turnos)

    # 1. Generar embedding usando la API de Groq (este proyecto usa Groq para embeddings)
    query_vec: List[float] = []
    # Use Groq embeddings endpoint to get vector without local torch
    # Use Groq embeddings endpoint to get vector without local torch
    # The groq client API for embeddings may differ depending on the package version; adjust if needed.
    emb_resp = None
    # Prefer a dedicated embedding model if provided; otherwise prefer GROQ_MODEL if it supports embedding
    # or select one from the account via models.list(). If no model is available, we'll skip embeddings.
    used_model = None
    if GROQ_EMBEDDING_MODEL:
        used_model = GROQ_EMBEDDING_MODEL
    elif GROQ_MODEL and 'embed' in (GROQ_MODEL or '').lower():
        used_model = GROQ_MODEL
    else:
        used_model = select_first_available_embedding_model()
    if used_model and EMBEDDING_BACKEND == 'groq':
        try:
            if groq_client:
                emb_resp = groq_client.embeddings.create(model=used_model, input=query)
            else:
                logger.debug('No groq client configured; skipping embeddings')
        except BadRequestError as e:
            # Model may not support embeddings; try to fall back to a dedicated embeddings model if available
            logger.warning("Embedding BadRequestError with model %s: %s", used_model, e)
            if used_model != 'embed-english-3.0':
                fallback_model = 'embed-english-3.0'
                try:
                    logger.info("Attempting fallback embedding model: %s", fallback_model)
                    emb_resp = groq_client.embeddings.create(model=fallback_model, input=query)
                except Exception:
                    logger.exception("Fallback embedding model also failed: %s", fallback_model)
                    emb_resp = None
            else:
                emb_resp = None
        except NotFoundError as e:
            # Model doesn't exist or not accessible by current API key
            logger.warning("Embedding NotFoundError with model %s: %s", used_model, e)
            # Try to pick a model by listing available models
            fallback_model = select_first_available_embedding_model()
            if fallback_model and fallback_model != used_model:
                try:
                    logger.info("Attempting fallback embedding model: %s", fallback_model)
                    emb_resp = groq_client.embeddings.create(model=fallback_model, input=query)
                except Exception:
                    logger.exception("Fallback embedding model also failed: %s", fallback_model)
                    emb_resp = None
            else:
                emb_resp = None
        except Exception as e:
            logger.exception("Embedding failed with model %s: %s", used_model, e)
            emb_resp = None
    else:
        logger.debug('No embedding model selected; skipping embedding in this request')

    # Normalize embedding response (support various client shapes)
    try:
        if emb_resp and hasattr(emb_resp, 'data') and isinstance(emb_resp.data, list) and len(emb_resp.data) > 0:
            query_vec = emb_resp.data[0].get('embedding', [])
        elif isinstance(emb_resp, dict) and emb_resp.get('data'):
            query_vec = emb_resp['data'][0].get('embedding', [])
        elif isinstance(emb_resp, list) and len(emb_resp) > 0 and isinstance(emb_resp[0], list):
            query_vec = emb_resp[0]
        else:
            query_vec = []
    except Exception:
        logger.exception('Failed to extract embedding vector from result: %s', getattr(emb_resp, 'data', emb_resp))
        query_vec = []


# NOTE: select_first_available_embedding_model() has been moved above
    
    # 2. Buscar contexto relevante en Supabase y WEB
    # 2. Buscar contexto relevante en Supabase (si está disponible). Si falla, continuamos sin contexto.
    context_fragments = []
    
    # A) Búsqueda Web (NUEVO)
    from web_search import search_web
    import asyncio
    try:
        logger.info("Performing web search for context...")
        # Ejecutar búsqueda en un hilo separado para no bloquear el loop principal
        loop = asyncio.get_running_loop()
        web_results = await loop.run_in_executor(None, search_web, query, 3)
        
        if web_results and "Error" not in web_results:
            context_fragments.append(f"=== RESULTADOS DE BÚSQUEDA WEB EN TIEMPO REAL ===\n{web_results}\n=============================================")
    except Exception as e:
        logger.error(f"Web search failed in AI handler: {e}")

    # B) Búsqueda en Base de Conocimiento (Supabase)
    try:
        if query_vec:
            res = supabase.rpc("search_knowledge_base", {"query_embedding": query_vec, "top_k": 3}).execute()
        else:
            # If we failed to get embeddings, fallback to returning the most recent entries
            res = supabase.table('knowledge_base').select('content,title').order('created_at', desc=True).limit(3).execute()
        if hasattr(res, 'data') and res.data:
            db_context = [item.get("content", "") for item in res.data]
            context_fragments.extend(db_context)
        elif isinstance(res, dict) and res.get('data'):
            db_context = [item.get("content", "") for item in res['data']]
            context_fragments.extend(db_context)
    except Exception as e:
        # Si no hay Supabase configurado o RPC falla, dejamos context_fragments vacío
        logger.exception('Error searching knowledge_base: %s', e)
        # No vaciamos context_fragments porque puede tener info de la web
    
    # TRUNCATE CONTEXT TO AVOID TOKEN OVERFLOW
    # Limit total context to approx 3000 chars
    final_fragments = []
    current_len = 0
    MAX_CONTEXT_LEN = 3000
    
    for frag in context_fragments:
        if current_len + len(frag) > MAX_CONTEXT_LEN:
            remaining = MAX_CONTEXT_LEN - current_len
            if remaining > 100:
                final_fragments.append(frag[:remaining] + "... [TRUNCATED]")
            break
        final_fragments.append(frag)
        current_len += len(frag)

    context = "\n\n".join(final_fragments)
    # 3. Construir prompt (MODO HACKER PROFESIONAL + SOLO ESPAÑOL)
    prompt = (
        "=== CONFIGURACIÓN OBLIGATORIA ===\n"
        "⚠️ IDIOMA: Responde SIEMPRE y ÚNICAMENTE en ESPAÑOL.\n"
        "⚠️ NO traduzcas. NO des la respuesta primero en inglés.\n"
        "⚠️ Si la información está en inglés, tradúcela al español.\n\n"
        
        "=== IDENTIDAD ===\n"
        "Soy 'KaliRoot' 💀 - Mente Hacker Elite especializada en Ciberseguridad Ofensiva.\n"
        "▸ Nivel: Red Team Senior / Pentester / Security Researcher\n"
        "▸ Estilo: Técnico, directo, sin rodeos\n"
        "▸ Filosofía: El conocimiento debe ser libre 🔓\n\n"
        
        "=== FORMATO DE RESPUESTA ===\n"
        "1. **ESTRUCTURA CLARA**:\n"
        "   • Usa saltos de línea para separar secciones\n"
        "   • Crea listas con bullets (▸ ◉ ➤ •)\n"
        "   • Títulos cortos con emojis relevantes\n\n"
        
        "2. **EMOJIS ESTRATÉGICOS** (usa variedad):\n"
        "   💀 🔓 🛡️ ⚡ 🔥 💻 🖥️ 📡 🌐 🔍 🗝️ ⚙️ 🎯 📌 ✅ ❌ ⚠️\n\n"
        
        "3. **CÓDIGO Y COMANDOS**:\n"
        "   • Usa bloques ```bash``` o ```python```\n"
        "   • Incluye comentarios explicativos\n"
        "   • Código funcional y probado\n"
        "   • Si generas un script, añade: [[SCRIPT: nombre.ext]]\n\n"
        
        "4. **ESTILO DE ESCRITURA**:\n"
        "   • Frases cortas y directas\n"
        "   • Explicaciones paso a paso\n"
        "   • Resalta términos técnicos en **negrita**\n"
        "   • Conciso pero completo\n\n"
        
        "5. **TEMAS QUE DOMINO**:\n"
        "   Pentesting, Exploits, Reverse Engineering, OSINT,\n"
        "   Wireless Hacking, Web Security, Network Security,\n"
        "   Malware Analysis, Criptografía, Social Engineering,\n"
        "   Kali Linux, Python, Bash, CTF\n\n"
        
        "6. **ENLACES** (solo si el usuario los pide):\n"
        "   Usa: [[BUTTON: Texto | URL]]\n\n"
        
        f"=== HISTORIAL ===\n{chat_history}\n\n"
        f"=== CONTEXTO WEB ===\n{context}\n\n"
        f"=== PREGUNTA ===\n{query}\n\n"
        "Responde en ESPAÑOL de forma clara, técnica y profesional:"
    )
    # 4. Llamar a Groq para completado (only if enabled)
    # Chat completion: use only Groq chat models
    # This bot uses only the Groq model specified in `GROQ_MODEL` for both embeddings and chat.
    chat_model = GROQ_MODEL
    # Attempt a single Groq chat model specified by config
    # If chat completions disabled, skip calling Groq and return fallback
    if not ENABLE_GROQ_CHAT or not groq_client:
        logger.info('Groq chat disabled or client missing; returning fallback')
        logger.debug('Returning FALLBACK_AI_TEXT: %s', FALLBACK_AI_TEXT)
        return FALLBACK_AI_TEXT
    try:
        response = groq_client.chat.completions.create(
            model=chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,  # Más preciso para información técnica
            max_tokens=2500,  # Aumentado para código extenso
            top_p=0.95
        )
        raw_text = None
        try:
            raw_text = response.choices[0].message.content if response.choices else None
        except Exception:
            logger.debug('Groq response not in expected format; trying dict access')
            if isinstance(response, dict):
                raw_text = response.get('choices', [{}])[0].get('message', {}).get('content')
        if not raw_text:
            logger.warning('Groq chat returned empty content; using fallback')
            return FALLBACK_AI_TEXT
        # Defensive sanitation: sometimes models return the string 'None' or 'null' as text,
        # treat that as an empty response and use the fallback.
        if isinstance(raw_text, str) and raw_text.strip().lower() in ('none', 'null', 'n/a'):
            logger.warning("Groq chat returned a placeholder string like 'None' or 'null'; using fallback")
            return FALLBACK_AI_TEXT
        # Ensure the response is safe and formatted for Telegram HTML parse mode
        try:
            formatted = format_ai_response_html(raw_text)
            if not formatted or formatted.strip().lower() in ('none', 'null', 'n/a'):
                logger.warning('Formatted AI response is empty or placeholder; using fallback instead')
                return FALLBACK_AI_TEXT
            
            # --- SAVE INTERACTION TO MEMORY ---
            await save_chat_interaction(user_id, query, raw_text) # Save raw text, not formatted
            
            return formatted
        except Exception:
            logger.exception('Failed to format AI response; returning fallback')
            return FALLBACK_AI_TEXT
    except Exception as e:
        logger.exception('Chat completion error with Groq model %s: %s', chat_model, e)
        # Log model availability if possible for easier debugging
        try:
            model_list = groq_client.models.list()  # type: ignore[attr-defined]
            if hasattr(model_list, 'data') and model_list.data:
                available_models = [m.id for m in model_list.data]
            elif isinstance(model_list, dict) and model_list.get('data'):
                available_models = [m.get('id') for m in model_list.get('data', [])]
            else:
                available_models = []
            logger.debug('Available Groq models: %s', available_models)
        except Exception:
            logger.debug('Could not list Groq models via API for debugging')
    if context:
        # Return the most relevant context fragment or a short summary
        # Guard against placeholder or empty text
        ctx_preview = context.splitlines()[0][:800] if context else ''
        formatted = format_ai_response_html((f"No puedo generar la respuesta ahora mismo, pero aquí tienes información relacionada:\n{ctx_preview}"))
        if not formatted or formatted.strip().lower() in ('none', 'null', 'n/a'):
            return FALLBACK_AI_TEXT
        return formatted
    return FALLBACK_AI_TEXT


def format_ai_response_html(text: str) -> str:
    """Format text to be safe for Telegram HTML parse mode.

    Steps:
    1️⃣ Escape HTML special characters.
    2️⃣ Convert fenced markdown code blocks (```...```) to <pre><code> blocks.
    3️⃣ Convert inline code (`...`) to <code> tags.
    4️⃣ Auto‑format common shell commands as separate <pre><code> blocks.
    5️⃣ Convert **bold** and __italic__ markdown to <b> and <i>.
    6️⃣ Truncate the final string to stay under Telegram's 4096‑character limit.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Normalise newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Split on markdown fenced code blocks so we can treat them specially
    parts = re.split(r"(```[\s\S]*?```)", text)
    formatted_parts: list[str] = []

    # Commands that should be rendered as full code blocks
    cmds = [
        "nmap", "apt", "apt-get", "pkg", "git", "python", "python3", "pip", "pip3",
        "bash", "sh", "zsh", "ls", "cd", "cat", "grep", "curl", "wget", "ssh", "scp",
        "ftp", "nc", "netcat", "ping", "systemctl", "service", "chmod", "chown",
        "rm", "cp", "mv", "mkdir", "touch", "nano", "vim", "sqlmap", "msfconsole",
        "msfvenom", "airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng",
        "hydra", "john", "hashcat", "wireshark", "burpsuite", "nikto", "gobuster",
        "dirb", "wfuzz", "radare2", "termux-setup-storage", "termux-change-repo",
    ]
    cmds_pattern = "|".join(re.escape(c) for c in cmds)
    cmd_regex = re.compile(
        rf"\\b({cmds_pattern})\\b((?:\\s+(?:[-a-zA-Z0-9_./*]+|\u0026lt;.*?\u0026gt;|\\[.*?\\]))+)",
        re.IGNORECASE,
    )

    for part in parts:
        # 1️⃣ Fenced code block – keep as‑is but escaped
        if part.startswith("```") and part.endswith("```"):
            content = part[3:-3]
            # Remove optional language specifier on the first line
            match = re.match(r"^[a-zA-Z0-9+\-#]+\n", content)
            if match:
                content = content[len(match.group(0)) :]
            escaped = html.escape(content.strip())
            formatted_parts.append(f"<pre><code>{escaped}</code></pre>")
            continue

        # 2️⃣ Normal prose – escape HTML first
        escaped_part = html.escape(part)
        
        # --- EMOJI ENHANCEMENT ---
        # Replace list bullets (*) with random aesthetic emojis
        # We use a simple deterministic replacement based on line hash or random to vary it per line
        import random
        bullet_emojis = ["🔹", "🔸", "▪️", "▫️", "➤", "⚡", "👉", "📍", "💥", "💠", "✅", "🔰", "🔱", "⚜️", "🌀"]
        
        def repl_bullet(m):
            return f"{random.choice(bullet_emojis)} "
            
        escaped_part = re.sub(r"^\s*\*\s", repl_bullet, escaped_part, flags=re.MULTILINE)
        
        # Inline code
        escaped_part = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped_part)
        # Auto‑format known commands as blocks (before bold/italic to avoid nesting)
        def repl_cmd(m):
            return f"<pre><code>{m.group(0)}</code></pre>"
        escaped_part = cmd_regex.sub(repl_cmd, escaped_part)
        # Bold – avoid wrapping inside a <pre> block
        def repl_bold(m):
            inner = m.group(1)
            if "<pre>" in inner:
                return inner
            return f"<b>{inner}</b>"
        escaped_part = re.sub(r"\*\*([^*]+)\*\*", repl_bold, escaped_part)
        # Italic
        escaped_part = re.sub(r"__([^_]+)__", r"<i>\1</i>", escaped_part)
        formatted_parts.append(escaped_part)

    result = "".join(formatted_parts)
    # 6️⃣ Truncate to stay safely under Telegram's 4096‑character limit
    max_len = 4000
    if len(result) > max_len:
        result = result[:max_len] + "..."
    return result
