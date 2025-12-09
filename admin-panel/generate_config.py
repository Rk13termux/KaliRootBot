#!/usr/bin/env python3
"""
Script para generar config.js del Admin Panel desde el archivo .env
Ejecutar desde la raíz del proyecto:
    python3 admin-panel/generate_config.py
"""

import os
from pathlib import Path

def load_env_file(env_path):
    """Lee un archivo .env y retorna un diccionario con las variables"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remover comillas si las tiene
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
    return env_vars

# Cargar .env desde la raíz del proyecto
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

if not env_path.exists():
    print(f"❌ No se encontró el archivo .env en {env_path}")
    print("   Crea el archivo .env con tus credenciales primero.")
    exit(1)

env_vars = load_env_file(env_path)

# Obtener las variables
supabase_url = env_vars.get("SUPABASE_URL", "")
supabase_key = env_vars.get("SUPABASE_SERVICE_KEY") or env_vars.get("SUPABASE_ANON_KEY", "")
bot_token = env_vars.get("TELEGRAM_BOT_TOKEN", "")
api_id = env_vars.get("TELEGRAM_API_ID", "")
api_hash = env_vars.get("TELEGRAM_API_HASH", "")
app_title = env_vars.get("TELEGRAM_APP_TITLE", "kaliroot")
short_name = env_vars.get("TELEGRAM_SHORT_NAME", "kaliroot")

# Generar el contenido de config.js
config_content = f'''/**
 * KaliRoot Admin Panel - Configuration File
 * Generated automatically from .env file
 * 
 * ⚠️ NO subir este archivo a repositorios públicos.
 * Ya está en .gitignore
 */

const ADMIN_CONFIG = {{
    // ===== SUPABASE =====
    supabase_url: '{supabase_url}',
    supabase_key: '{supabase_key}',
    
    // ===== TELEGRAM BOT =====
    bot_token: '{bot_token}',
    
    // ===== TELEGRAM API =====
    telegram_api_id: '{api_id}',
    telegram_api_hash: '{api_hash}',
    telegram_app_title: '{app_title}',
    telegram_short_name: '{short_name}',
    
    // ===== CONFIGURACIÓN =====
    auto_login: true,
    default_credits: 20,
    subscription_days: 30
}};

if (typeof window !== 'undefined') {{
    window.ADMIN_CONFIG = ADMIN_CONFIG;
}}
'''

# Guardar en admin-panel/config.js
config_path = Path(__file__).parent / 'config.js'
config_path.write_text(config_content)

print(f"✅ Archivo generado: {config_path}")
print(f"   Supabase URL: {supabase_url[:30]}..." if supabase_url else "   ⚠️ Supabase URL vacía")
print(f"   Bot Token: {'***' + bot_token[-6:] if bot_token else '⚠️ No configurado'}")
print(f"   API ID: {api_id if api_id else '⚠️ No configurado'}")
print()
print("🚀 Ahora abre el Admin Panel y hará login automático:")
print("   http://localhost:8080")
