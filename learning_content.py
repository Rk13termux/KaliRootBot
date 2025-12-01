"""
Contenido Masivo para la Ruta de Aprendizaje de Kali Linux.
Estructura: 10 Secciones x 10 Módulos = 100 Módulos.
Sección 1: Gratuita.
Secciones 2-10: Premium.
"""

# Placeholder link (User provided)
DEFAULT_LINK = "https://telegra.ph/hola-mundo-de-kaliroot-12-01"
# Placeholder image (More stable URL)
DEFAULT_IMG = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Kali-dragon-icon.svg/1200px-Kali-dragon-icon.svg.png"

SECTIONS = {
    1: {"title": "🌱 Nivel 1: Génesis del Hacker", "free": True},
    2: {"title": "👻 Nivel 2: Fantasma en la Red", "free": False},
    3: {"title": "👁️ Nivel 3: Ojos que Todo lo Ven", "free": False},
    4: {"title": "⚔️ Nivel 4: El Arte de la Intrusión", "free": False},
    5: {"title": "🔨 Nivel 5: Rompiendo Muros", "free": False},
    6: {"title": "🎭 Nivel 6: Maestro de Marionetas", "free": False},
    7: {"title": "🧠 Nivel 7: Ingeniería Social Oscura", "free": False},
    8: {"title": "🔐 Nivel 8: Criptografía y Secretos", "free": False},
    9: {"title": "👑 Nivel 9: Post-Explotación Letal", "free": False},
    10: {"title": "⚡ Nivel 10: Dios del Root", "free": False},
}

# Generamos los 100 módulos con títulos persuasivos
MODULES = {}

# --- SECCIÓN 1: GÉNESIS (GRATIS) ---
MODULES[1] = {"section": 1, "title": "El Despertar: ¿Qué es realmente Kali?", "desc": "Instalación y primeros pasos en el sistema operativo de los dioses.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[2] = {"section": 1, "title": "La Terminal: Tu Nueva Lengua Materna", "desc": "Olvida el mouse. Aprende a hablar con la máquina directamente.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[3] = {"section": 1, "title": "Permisos de Dios: Entendiendo Root", "desc": "El poder absoluto conlleva responsabilidad absoluta. Gestión de usuarios.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[4] = {"section": 1, "title": "El Mapa del Tesoro: Sistema de Archivos", "desc": "Dónde se esconden los secretos en Linux. Navegación experta.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[5] = {"section": 1, "title": "Redes 101: Cómo Hablan las Máquinas", "desc": "IPs, Puertos y Protocolos. La base de todo ataque.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[6] = {"section": 1, "title": "Tu Primer Laboratorio Seguro", "desc": "Crea un entorno de pruebas para no ir a la cárcel.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[7] = {"section": 1, "title": "Comandos Letales Básicos", "desc": "Herramientas de terminal que todo hacker debe memorizar.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[8] = {"section": 1, "title": "Editores de Texto: Nano y Vim", "desc": "Escribe código y scripts sin salir de la consola.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[9] = {"section": 1, "title": "Automatización Simple con Bash", "desc": "Haz que la máquina trabaje por ti. Tus primeros scripts.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[10] = {"section": 1, "title": "Ética Hacker: El Código de Honor", "desc": "La diferencia entre un profesional y un criminal.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}

# --- SECCIÓN 2: ANONIMATO ---
MODULES[11] = {"section": 2, "title": "La Capa de Invisibilidad: VPNs", "desc": "Oculta tu origen antes de lanzar el primer paquete.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[12] = {"section": 2, "title": "Tor y la Deep Web", "desc": "Navegación en cebolla. Entrando al abismo sin ser visto.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[13] = {"section": 2, "title": "Proxychains: Saltando Fronteras", "desc": "Encadena tu conexión por múltiples servidores para ser irrastreable.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[14] = {"section": 2, "title": "MAC Spoofing: Cambiando tu ADN", "desc": "Falsifica la identidad física de tu tarjeta de red.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[15] = {"section": 2, "title": "Navegadores Anti-Huella", "desc": "Configuración de Firefox para privacidad extrema.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[16] = {"section": 2, "title": "Correos Desechables y Encriptados", "desc": "Comunicaciones seguras con PGP y ProtonMail.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[17] = {"section": 2, "title": "Limpieza de Rastros (Logs)", "desc": "Cómo borrar tus huellas del sistema después de entrar.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[18] = {"section": 2, "title": "Sistemas Operativos Amnésicos (Tails)", "desc": "El sistema que olvida todo al apagarse.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[19] = {"section": 2, "title": "Criptomonedas y Pagos Anónimos", "desc": "Fundamentos de economía en la sombra.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[20] = {"section": 2, "title": "OpSec: Seguridad Operacional", "desc": "Mentalidad paranoica para sobrevivir en la red.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}

# --- SECCIÓN 3: OSINT ---
MODULES[21] = {"section": 3, "title": "Google Dorks: Buscando Secretos", "desc": "Comandos de búsqueda avanzados para encontrar passwords y bases de datos.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[22] = {"section": 3, "title": "TheHarvester: Cosechando Emails", "desc": "Recolecta objetivos corporativos en segundos.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[23] = {"section": 3, "title": "Shodan: El Buscador del IoT", "desc": "Encuentra cámaras, servidores y neveras conectadas a internet.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[24] = {"section": 3, "title": "Maltego: Mapeando Relaciones", "desc": "Visualiza conexiones entre personas, dominios y servidores.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[25] = {"section": 3, "title": "Metadatos: Lo que las Fotos Dicen", "desc": "Extrae ubicación GPS y autoría de archivos con ExifTool.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[26] = {"section": 3, "title": "Reconocimiento de DNS", "desc": "Descubre la infraestructura oculta de una web.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[27] = {"section": 3, "title": "Ingeniería Social en Redes Sociales", "desc": "Cómo obtener información de perfiles públicos.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[28] = {"section": 3, "title": "Wayback Machine: Viaje en el Tiempo", "desc": "Ver versiones antiguas de webs para encontrar fallos viejos.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[29] = {"section": 3, "title": "Escaneo Pasivo vs Activo", "desc": "Diferencias clave para no alertar a las defensas.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[30] = {"section": 3, "title": "Creando tu Dossier de Objetivo", "desc": "Organiza la inteligencia recolectada para el ataque.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}

# --- SECCIÓN 4: ESCANEO ---
MODULES[31] = {"section": 4, "title": "Nmap: El Rey de los Escáneres", "desc": "Descubre puertos abiertos y servicios vulnerables.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[32] = {"section": 4, "title": "Escaneos Sigilosos (Stealth)", "desc": "Cómo escanear sin ser detectado por el Firewall.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[33] = {"section": 4, "title": "Fingerprinting de SO", "desc": "Adivina qué sistema operativo usa la víctima.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[34] = {"section": 4, "title": "Scripts de Nmap (NSE)", "desc": "Automatiza la detección de vulnerabilidades con scripts.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[35] = {"section": 4, "title": "Masscan: Escaneando Internet", "desc": "Velocidad extrema para rangos de IP masivos.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[36] = {"section": 4, "title": "Enumeración SMB y NetBIOS", "desc": "Explorando redes Windows compartidas.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[37] = {"section": 4, "title": "Enumeración SNMP", "desc": "Extrayendo información de routers e impresoras.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[38] = {"section": 4, "title": "Detección de Firewalls e IPS", "desc": "Saber si te están bloqueando y cómo evadirlo.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[39] = {"section": 4, "title": "Mapeo de Redes con Zenmap", "desc": "Visualización gráfica de la topología de red.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}
MODULES[40] = {"section": 4, "title": "Análisis de Vulnerabilidades con Nessus", "desc": "Introducción a escáneres automatizados profesionales.", "img": DEFAULT_IMG, "link": DEFAULT_LINK}

# --- Rellenamos el resto con placeholders genéricos para completar 100 ---
for i in range(41, 101):
    section_id = (i - 1) // 10 + 1
    MODULES[i] = {
        "section": section_id,
        "title": f"Técnica Avanzada #{i}",
        "desc": "Contenido clasificado de alto nivel. Solo para expertos.",
        "img": DEFAULT_IMG,
        "link": DEFAULT_LINK
    }
