# 🛡️ KaliRoot Admin Panel

Panel de administración web para gestionar el bot KaliRoot y la MiniApp de Telegram.

## 📋 Características

- ✅ **Dashboard** - Vista general con estadísticas
- ✅ **Gestión de Usuarios** - Ver, editar, buscar y exportar usuarios
- ✅ **Suscripciones** - Activar/desactivar suscripciones manualmente
- ✅ **Recursos de Descarga** - Gestionar archivos de Google Drive
- ✅ **Módulos de Aprendizaje** - Ver progreso de los usuarios
- ✅ **Insignias** - Ver insignias disponibles
- ✅ **Log de Auditoría** - Ver actividad del sistema
- ✅ **Envío de mensajes** - Enviar mensajes directos a usuarios

## 🚀 Cómo Usar

### 1. Ejecutar la tabla de recursos en Supabase

Antes de usar el panel, ejecuta el script SQL para crear la tabla de recursos:

1. Ve a tu proyecto en [Supabase](https://supabase.com/dashboard)
2. Abre el **SQL Editor**
3. Copia y pega el contenido de `create_resources_table.sql`
4. Ejecuta el script

### 2. Abrir el Panel

**Opción A: Directamente en el navegador**
```bash
# Abre el archivo index.html en tu navegador
firefox admin-panel/index.html
# o
google-chrome admin-panel/index.html
```

**Opción B: Con un servidor local (recomendado)**
```bash
cd admin-panel
python3 -m http.server 8080
# Abre http://localhost:8080 en tu navegador
```

### 3. Conectar a Supabase

En la pantalla de login, ingresa:

| Campo | Descripción | Dónde encontrarlo |
|-------|-------------|-------------------|
| **Supabase URL** | URL de tu proyecto | Supabase > Settings > API > Project URL |
| **Supabase Service Key** | Clave de servicio | Supabase > Settings > API > service_role (secret) |
| **Bot Token** (opcional) | Token de Telegram | @BotFather en Telegram |

⚠️ **IMPORTANTE**: Usa la **Service Key** (service_role), NO la anon key, para tener acceso completo a las tablas.

## 📦 Gestión de Recursos (Google Drive)

### Cómo agregar un archivo:

1. **Sube el archivo a Google Drive**
2. **Haz clic derecho** → Compartir → "Cualquier persona con el enlace puede ver"
3. **Copia el ID del archivo** del enlace:
   ```
   https://drive.google.com/file/d/1ABC123xyz789/view
                                   ↑↑↑↑↑↑↑↑↑↑↑↑↑
                                   Este es el ID
   ```
4. **En el Admin Panel** → Recursos → ➕ Nuevo Recurso
5. **Completa los campos**:
   - Título: Nombre del recurso
   - Icono: Un emoji (🐉, 📱, 📡, etc.)
   - Descripción: Breve descripción
   - Drive File ID: Pega el ID copiado
   - Tamaño: Ej. "2.3 GB"
   - Categoría: Selecciona una
   - Activo: ✅ para que aparezca en la MiniApp

### Los recursos aparecerán automáticamente en la MiniApp

Una vez guardados, los recursos se reflejarán en el Dashboard Premium de la MiniApp.

## 🔧 Estructura del Panel

```
admin-panel/
├── index.html              # Página principal
├── admin.css               # Estilos
├── admin.js                # Lógica JavaScript
├── create_resources_table.sql  # Script SQL para Supabase
└── README.md               # Esta documentación
```

## 📊 Tablas de Supabase Requeridas

| Tabla | Descripción |
|-------|-------------|
| `usuarios` | Usuarios del bot |
| `download_resources` | Recursos de descarga (crear con el SQL) |
| `user_modules` | Progreso de aprendizaje |
| `badges` | Definición de insignias |
| `user_badges` | Insignias ganadas por usuarios |
| `audit_log` | Registro de actividad |

## 🔐 Seguridad

- Las credenciales se guardan **solo en localStorage** de tu navegador
- La opción "Recordar credenciales" es opcional
- El panel funciona **completamente local** (no envía datos a terceros)
- Usa siempre la Service Key para operaciones de escritura

## 💡 Tips

1. **Actualizar datos**: Usa el botón 🔄 en la barra superior
2. **Buscar usuarios**: Escribe en el campo de búsqueda (por ID, nombre o username)
3. **Exportar usuarios**: Botón "📥 Exportar CSV" en la sección de usuarios
4. **Probar enlaces de Drive**: Botón 🔗 en cada recurso

## ❓ Solución de Problemas

**"La tabla download_resources no existe"**
→ Ejecuta el script `create_resources_table.sql` en Supabase

**"Error de conexión"**
→ Verifica que la URL y la Service Key sean correctas

**"No aparecen los recursos en la MiniApp"**
→ Verifica que el recurso esté marcado como "Activo"

## 📱 Telegram API Server (MTProto)

Para acceder a funciones avanzadas como listar canales y grupos administrados, necesitas ejecutar el servidor API de Python.

### Instalación

```bash
pip install telethon fastapi uvicorn aiofiles
```

### Ejecución

```bash
python3 admin-panel/api_server.py
```

El servidor se ejecutará en `http://localhost:8081`

### Endpoints Disponibles

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/health` | Estado del servidor |
| `GET /api/auth/status` | Verificar si estás autenticado |
| `POST /api/auth/code` | Enviar código de verificación |
| `POST /api/auth/verify` | Verificar código |
| `GET /api/me` | Tu información de cuenta |
| `GET /api/dialogs` | Todos los chats |
| `GET /api/channels` | Canales administrados |
| `GET /api/groups` | Grupos |
| `GET /api/stats` | Estadísticas generales |
| `GET /api/chat/{id}` | Info de un chat |
| `GET /api/members/{id}` | Miembros de un chat |
| `POST /api/send` | Enviar mensaje |

### Primera Autenticación

1. Ve a la sección "Telegram" en el Admin Panel
2. Ingresa tu número de teléfono con código de país (ej: +51912345678)
3. Recibirás un código en tu Telegram
4. Ingresa el código
5. Si tienes 2FA, ingresa tu contraseña

La sesión se guarda automáticamente para futuras visitas.

### Swagger UI

Accede a `http://localhost:8081/docs` para ver la documentación interactiva de la API.

---

Desarrollado para **KaliRoot Bot** 🐉
