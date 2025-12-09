#!/usr/bin/env python3
"""
KaliRoot Admin API Server
Servidor backend para el Admin Panel que conecta con Telegram API (MTProto)
Usa Telethon para acceder a TODA la funcionalidad de Telegram.

Ejecutar:
    pip install telethon fastapi uvicorn aiofiles
    python3 admin-panel/api_server.py

Endpoints:
    GET  /api/me              - Info de la cuenta
    GET  /api/dialogs         - Lista de chats/canales/grupos
    GET  /api/channels        - Solo canales administrados
    GET  /api/groups          - Solo grupos
    GET  /api/stats           - Estadísticas generales
    GET  /api/chat/{id}       - Info de un chat específico
    GET  /api/members/{id}    - Miembros de un chat
    POST /api/send            - Enviar mensaje
    POST /api/auth/code       - Enviar código de verificación
    POST /api/auth/verify     - Verificar código
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

# Telethon imports
from telethon import TelegramClient
from telethon.tl.types import (
    Channel, Chat, User,
    ChannelParticipantsAdmins,
    ChannelParticipantsRecent
)
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Load config
def load_config():
    """Load config from config.js or environment variables"""
    config_path = Path(__file__).parent / 'config.js'
    
    if config_path.exists():
        content = config_path.read_text()
        # Parse JavaScript object
        import re
        
        def get_value(key):
            match = re.search(rf"{key}:\s*['\"]([^'\"]*)['\"]", content)
            return match.group(1) if match else ''
        
        return {
            'api_id': get_value('telegram_api_id'),
            'api_hash': get_value('telegram_api_hash'),
            'bot_token': get_value('bot_token'),
        }
    
    # Fallback to environment variables
    return {
        'api_id': os.getenv('TELEGRAM_API_ID', ''),
        'api_hash': os.getenv('TELEGRAM_API_HASH', ''),
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    }

config = load_config()

# Validate config
if not config['api_id'] or not config['api_hash']:
    print("⚠️ TELEGRAM_API_ID y TELEGRAM_API_HASH son requeridos")
    print("   Configúralos en config.js o como variables de entorno")

# Initialize FastAPI
app = FastAPI(
    title="KaliRoot Admin API",
    description="Backend API para el Admin Panel con Telegram MTProto",
    version="1.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session file for persistent login
SESSION_FILE = Path(__file__).parent / 'telegram_session'

# Global client
client: Optional[TelegramClient] = None
phone_code_hash: Optional[str] = None
pending_phone: Optional[str] = None

# ===== MODELS =====
class AuthPhoneRequest(BaseModel):
    phone: str

class AuthCodeRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None

class SendMessageRequest(BaseModel):
    chat_id: int
    message: str

# ===== HELPER FUNCTIONS =====
async def get_client() -> TelegramClient:
    global client
    
    if client is None or not client.is_connected():
        client = TelegramClient(
            str(SESSION_FILE),
            int(config['api_id']),
            config['api_hash']
        )
        await client.connect()
    
    return client

async def ensure_authorized():
    """Check if client is authorized, raise error if not"""
    c = await get_client()
    if not await c.is_user_authorized():
        raise HTTPException(status_code=401, detail="No autorizado. Usa /api/auth/code primero.")
    return c

# ===== AUTH ENDPOINTS =====
@app.get("/api/auth/status")
async def auth_status():
    """Check if session is active"""
    try:
        c = await get_client()
        authorized = await c.is_user_authorized()
        
        if authorized:
            me = await c.get_me()
            return {
                "authorized": True,
                "user": {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username,
                    "phone": me.phone
                }
            }
        
        return {"authorized": False}
    except Exception as e:
        return {"authorized": False, "error": str(e)}

@app.post("/api/auth/code")
async def send_auth_code(request: AuthPhoneRequest):
    """Send authentication code to phone"""
    global phone_code_hash, pending_phone
    
    try:
        c = await get_client()
        result = await c.send_code_request(request.phone)
        phone_code_hash = result.phone_code_hash
        pending_phone = request.phone
        
        return {
            "success": True,
            "message": f"Código enviado a {request.phone}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/verify")
async def verify_auth_code(request: AuthCodeRequest):
    """Verify the authentication code"""
    global phone_code_hash, pending_phone
    
    try:
        c = await get_client()
        
        await c.sign_in(
            phone=request.phone or pending_phone,
            code=request.code,
            phone_code_hash=phone_code_hash
        )
        
        me = await c.get_me()
        
        return {
            "success": True,
            "user": {
                "id": me.id,
                "first_name": me.first_name,
                "username": me.username
            }
        }
    except SessionPasswordNeededError:
        # 2FA is enabled
        if request.password:
            await c.sign_in(password=request.password)
            me = await c.get_me()
            return {
                "success": True,
                "user": {"id": me.id, "first_name": me.first_name}
            }
        raise HTTPException(status_code=400, detail="Se requiere contraseña 2FA")
    except PhoneCodeInvalidError:
        raise HTTPException(status_code=400, detail="Código inválido")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/logout")
async def logout():
    """Logout and delete session"""
    global client
    
    try:
        if client:
            await client.log_out()
            client = None
        
        # Delete session file
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        session_journal = Path(str(SESSION_FILE) + '.session')
        if session_journal.exists():
            session_journal.unlink()
        
        return {"success": True, "message": "Sesión cerrada"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== DATA ENDPOINTS =====
@app.get("/api/me")
async def get_me():
    """Get current user info"""
    c = await ensure_authorized()
    me = await c.get_me()
    
    return {
        "id": me.id,
        "first_name": me.first_name,
        "last_name": me.last_name,
        "username": me.username,
        "phone": me.phone,
        "is_bot": me.bot,
        "is_premium": getattr(me, 'premium', False)
    }

@app.get("/api/dialogs")
async def get_dialogs(limit: int = Query(100, le=500)):
    """Get all dialogs (chats, groups, channels)"""
    c = await ensure_authorized()
    
    dialogs = await c.get_dialogs(limit=limit)
    
    result = []
    for dialog in dialogs:
        entity = dialog.entity
        dialog_data = {
            "id": dialog.id,
            "name": dialog.name,
            "unread_count": dialog.unread_count,
            "pinned": dialog.pinned,
            "archived": dialog.archived,
        }
        
        if hasattr(entity, 'megagroup'):
            dialog_data["type"] = "supergroup" if entity.megagroup else "channel"
            dialog_data["is_channel"] = not entity.megagroup
            dialog_data["is_admin"] = getattr(entity, 'admin_rights', None) is not None or getattr(entity, 'creator', False)
            dialog_data["username"] = getattr(entity, 'username', None)
            dialog_data["participants_count"] = getattr(entity, 'participants_count', None)
        elif isinstance(entity, Chat):
            dialog_data["type"] = "group"
            dialog_data["participants_count"] = getattr(entity, 'participants_count', None)
        elif isinstance(entity, User):
            dialog_data["type"] = "private"
            dialog_data["is_bot"] = entity.bot
        
        result.append(dialog_data)
    
    return {"dialogs": result, "count": len(result)}

@app.get("/api/channels")
async def get_channels():
    """Get only channels where user is admin"""
    c = await ensure_authorized()
    
    dialogs = await c.get_dialogs()
    
    channels = []
    for dialog in dialogs:
        entity = dialog.entity
        if hasattr(entity, 'megagroup') and not entity.megagroup:
            is_admin = getattr(entity, 'admin_rights', None) is not None or getattr(entity, 'creator', False)
            
            # Get full channel info for more details
            try:
                full = await c(GetFullChannelRequest(entity))
                participants = full.full_chat.participants_count
            except:
                participants = getattr(entity, 'participants_count', 0)
            
            channels.append({
                "id": dialog.id,
                "name": dialog.name,
                "username": getattr(entity, 'username', None),
                "participants_count": participants,
                "is_admin": is_admin,
                "is_creator": getattr(entity, 'creator', False),
            })
    
    return {"channels": channels, "count": len(channels)}

@app.get("/api/groups")
async def get_groups():
    """Get only groups (regular and super)"""
    c = await ensure_authorized()
    
    dialogs = await c.get_dialogs()
    
    groups = []
    for dialog in dialogs:
        entity = dialog.entity
        is_group = isinstance(entity, Chat) or (hasattr(entity, 'megagroup') and entity.megagroup)
        
        if is_group:
            is_admin = getattr(entity, 'admin_rights', None) is not None or getattr(entity, 'creator', False)
            
            groups.append({
                "id": dialog.id,
                "name": dialog.name,
                "username": getattr(entity, 'username', None),
                "participants_count": getattr(entity, 'participants_count', None),
                "is_admin": is_admin,
                "is_supergroup": hasattr(entity, 'megagroup') and entity.megagroup,
            })
    
    return {"groups": groups, "count": len(groups)}

@app.get("/api/stats")
async def get_stats():
    """Get general statistics"""
    c = await ensure_authorized()
    
    dialogs = await c.get_dialogs()
    
    stats = {
        "total_dialogs": len(dialogs),
        "private_chats": 0,
        "groups": 0,
        "supergroups": 0,
        "channels": 0,
        "bots": 0,
        "unread_messages": 0,
        "admin_channels": 0,
        "admin_groups": 0,
    }
    
    for dialog in dialogs:
        entity = dialog.entity
        stats["unread_messages"] += dialog.unread_count
        
        if isinstance(entity, User):
            if entity.bot:
                stats["bots"] += 1
            else:
                stats["private_chats"] += 1
        elif isinstance(entity, Chat):
            stats["groups"] += 1
        elif hasattr(entity, 'megagroup'):
            is_admin = getattr(entity, 'admin_rights', None) is not None or getattr(entity, 'creator', False)
            if entity.megagroup:
                stats["supergroups"] += 1
                if is_admin:
                    stats["admin_groups"] += 1
            else:
                stats["channels"] += 1
                if is_admin:
                    stats["admin_channels"] += 1
    
    return stats

@app.get("/api/chat/{chat_id}")
async def get_chat_info(chat_id: int):
    """Get detailed info about a specific chat"""
    c = await ensure_authorized()
    
    try:
        entity = await c.get_entity(chat_id)
        
        info = {
            "id": entity.id,
            "type": "unknown"
        }
        
        if isinstance(entity, User):
            info["type"] = "user"
            info["first_name"] = entity.first_name
            info["last_name"] = entity.last_name
            info["username"] = entity.username
            info["phone"] = entity.phone
            info["is_bot"] = entity.bot
        elif isinstance(entity, Chat):
            info["type"] = "group"
            info["title"] = entity.title
            info["participants_count"] = entity.participants_count
        elif isinstance(entity, Channel):
            info["type"] = "supergroup" if entity.megagroup else "channel"
            info["title"] = entity.title
            info["username"] = entity.username
            
            # Get full info
            try:
                full = await c(GetFullChannelRequest(entity))
                info["participants_count"] = full.full_chat.participants_count
                info["about"] = full.full_chat.about
            except:
                pass
        
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/members/{chat_id}")
async def get_chat_members(chat_id: int, limit: int = Query(100, le=1000)):
    """Get members of a chat/channel"""
    c = await ensure_authorized()
    
    try:
        entity = await c.get_entity(chat_id)
        
        participants = await c.get_participants(entity, limit=limit)
        
        members = []
        for p in participants:
            members.append({
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "username": p.username,
                "is_bot": p.bot,
            })
        
        return {"members": members, "count": len(members)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/send")
async def send_message(request: SendMessageRequest):
    """Send a message to a chat"""
    c = await ensure_authorized()
    
    try:
        result = await c.send_message(request.chat_id, request.message)
        return {"success": True, "message_id": result.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== HEALTH CHECK =====
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "config_loaded": bool(config['api_id'])
    }

# ===== MAIN =====
if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando KaliRoot Admin API Server...")
    print(f"   API ID configurado: {'✅' if config['api_id'] else '❌'}")
    print(f"   API Hash configurado: {'✅' if config['api_hash'] else '❌'}")
    print()
    print("📡 Endpoints disponibles:")
    print("   http://localhost:8081/api/health")
    print("   http://localhost:8081/api/auth/status")
    print("   http://localhost:8081/docs (Swagger UI)")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8081)
