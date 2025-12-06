import json
import os
import logging
from ai_handler import groq_client, GROQ_MODEL
import learning_content

logger = logging.getLogger(__name__)

CACHE_FILE = 'storage/learning_cache.json'

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_cache(cache):
    os.makedirs('storage', exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

async def generate_lesson(module_id: int, force_refresh: bool = False) -> str:
    """Generates AI content for a module. Returns HTML fragment."""
    
    # 1. Check Cache
    cache = load_cache()
    cache_key = str(module_id)
    
    if not force_refresh and cache_key in cache:
        logger.info(f"Serving module {module_id} from cache")
        return cache[cache_key]

    # 2. Get Module Info
    module_info = learning_content.MODULES.get(module_id)
    if not module_info:
        return "<p>Error: Módulo no encontrado.</p>"

    title = module_info['title']
    desc = module_info['desc']
    
    # 3. Construct Prompt
    prompt = f"""
    Eres un Instructor de Élite en Ciberseguridad Ofensiva y Hacking Ético (Kali Linux).
    Tu misión es generar el contenido educativo detallado para el módulo de aprendizaje:
    
    TÍTULO: {title}
    DESCRIPCIÓN: {desc}
    
    INSTRUCCIONES DE FORMATO:
    1. Tu respuesta debe ser EXCLUSIVAMENTE código HTML válido para inyectar en un contenedor. NO devuelvas Markdown ni bloques ```html```.
    2. Usa la siguiente estructura HTML (puedes adaptar el contenido pero mantén las clases para el CSS):
    
    <div class="content-block">
        <h3 class="section-title">🔹 Conceptos Fundamentales</h3>
        <p>[Explicación teórica profunda pero accesible. Usa negritas para términos clave. Al menos 2 párrafos.]</p>
    </div>
    
    <div class="content-block">
        <h3 class="section-title">💻 Sintaxis y Comandos</h3>
        <p>El comando principal para esta herramienta es:</p>
        <div class="code-block">
            <pre><code class="language-bash">[Comando de ejemplo realista]</code></pre>
        </div>
        <ul class="params-list">
            <li><b>-flag1</b>: Explicación de qué hace.</li>
            <li><b>-flag2</b>: Explicación de qué hace.</li>
        </ul>
    </div>
    
    <div class="content-block">
        <h3 class="section-title">🚀 Escenario de Uso Real</h3>
        <p>[Describe una situación de pentesting donde usarías esto y por qué.]</p>
    </div>
    
    <div class="tip-box">
        <div class="tip-title">💡 Pro Tip (Nivel Hacker)</div>
        <p>[Un consejo avanzado, truco o advertencia de seguridad importante relacionado con este módulo.]</p>
    </div>
    
    RESTRICCIONES:
    - NO uses las etiquetas <html>, <head>, <body>. Empieza directamente con los divs.
    - NO inventes comandos inexistentes. Usa herramientas reales de Kali Linux (nmap, aircrack-ng, metasploit, etc.) según corresponda al título.
    - El tono debe ser profesional, técnico y motivador ("Hacker style").
    """
    
    # 4. Call AI
    try:
        if not groq_client:
            return "<div class='error-box'>⚠️ Error: Sistema de IA no configurado (API Key faltante).</div>"
            
        logger.info(f"Generating AI content for module {module_id}...")
        
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6, # Balance entre creatividad y precisión técnica
            max_tokens=2500,
            top_p=1.0
        )
        
        content = response.choices[0].message.content
        
        # Clean up if AI wraps in ```html ... ``` or ```
        content = content.replace("```html", "").replace("```", "").strip()
        
        # Validate minimal HTML content
        if "<div" not in content:
            # Fallback formatting just in case
            content = f"<div>{content}</div>"
        
        # 5. Save Cache
        cache[cache_key] = content
        save_cache(cache)
        
        return content
        
    except Exception as e:
        logger.error(f"Error generating AI lesson: {e}")
        return f"<div class='error-box'>⚠️ Error generando contenido con IA: {str(e)}</div>"
