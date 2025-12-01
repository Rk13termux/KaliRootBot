"""
Contenido Masivo para la Ruta de Aprendizaje de Kali Linux.
Estructura: 10 Secciones x 10 Módulos = 100 Módulos.
Títulos Persuasivos y Profesionales.
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

MODULES = {}

def add_mod(id, sec, title, desc):
    MODULES[id] = {"section": sec, "title": title, "desc": desc, "img": DEFAULT_IMG, "link": DEFAULT_LINK}

# --- NIVEL 1: GÉNESIS ---
add_mod(1, 1, "El Despertar: Instalando Kali", "Configura tu entorno de guerra virtual.")
add_mod(2, 1, "La Terminal: Tu Nueva Lengua", "Domina la línea de comandos como un nativo.")
add_mod(3, 1, "Permisos de Dios: Root y Sudo", "El poder absoluto conlleva responsabilidad absoluta.")
add_mod(4, 1, "El Mapa del Tesoro: Filesystem", "Navega por las entrañas de Linux sin perderte.")
add_mod(5, 1, "Redes 101: El Lenguaje de Internet", "IPs, Puertos y Protocolos explicados para hackers.")
add_mod(6, 1, "Tu Primer Laboratorio Seguro", "Crea un sandbox para romper cosas sin ir a la cárcel.")
add_mod(7, 1, "Comandos Letales Básicos", "Herramientas esenciales que usarás cada día.")
add_mod(8, 1, "Editores de Código: Nano y Vim", "Escribe scripts y exploits sin salir de la consola.")
add_mod(9, 1, "Automatización con Bash Scripting", "Haz que la máquina trabaje por ti mientras duermes.")
add_mod(10, 1, "Ética Hacker: El Código de Honor", "La línea delgada entre un profesional y un criminal.")

# --- NIVEL 2: ANONIMATO ---
add_mod(11, 2, "La Capa de Invisibilidad: VPNs", "Cifra tu tráfico y oculta tu origen.")
add_mod(12, 2, "Tor: Navegando en las Sombras", "Entra a la Deep Web sin dejar rastro.")
add_mod(13, 2, "Proxychains: Saltando Fronteras", "Rebota tu conexión por el mundo para ser irrastreable.")
add_mod(14, 2, "MAC Spoofing: Identidad Falsa", "Cambia tu huella digital física en la red.")
add_mod(15, 2, "Navegadores Anti-Rastreo", "Configuración paranoica de Firefox y Tor Browser.")
add_mod(16, 2, "Comunicaciones Encriptadas (PGP)", "Envía mensajes que solo el destinatario puede leer.")
add_mod(17, 2, "Limpieza Forense de Logs", "Borra tus huellas del sistema al salir.")
add_mod(18, 2, "Tails OS: El Sistema Amnésico", "Un sistema operativo que olvida todo al apagarse.")
add_mod(19, 2, "Criptomonedas y Pagos Anónimos", "Economía en la sombra: Bitcoin y Monero.")
add_mod(20, 2, "OpSec: Mentalidad de Espía", "Hábitos de seguridad operacional para sobrevivir.")

# --- NIVEL 3: OSINT ---
add_mod(21, 3, "Google Dorks: Búsqueda Avanzada", "Encuentra contraseñas y archivos ocultos en Google.")
add_mod(22, 3, "TheHarvester: Cosecha de Datos", "Recolecta emails y subdominios automáticamente.")
add_mod(23, 3, "Shodan: El Buscador del IoT", "Encuentra cámaras y servidores vulnerables.")
add_mod(24, 3, "Maltego: Mapeo de Relaciones", "Visualiza conexiones entre personas y empresas.")
add_mod(25, 3, "Metadatos: Secretos en Fotos", "Extrae ubicación GPS y autoría de archivos.")
add_mod(26, 3, "Reconocimiento de DNS", "Descubre la infraestructura oculta de una web.")
add_mod(27, 3, "OSINT en Redes Sociales", "Investigación de perfiles en Facebook, Twitter y LinkedIn.")
add_mod(28, 3, "Wayback Machine: Viaje Temporal", "Analiza versiones antiguas de sitios web.")
add_mod(29, 3, "Escaneo Pasivo vs Activo", "Diferencias clave para no alertar al objetivo.")
add_mod(30, 3, "Creando el Dossier del Objetivo", "Organiza la inteligencia para el ataque.")

# --- NIVEL 4: ESCANEO ---
add_mod(31, 4, "Nmap: El Rey del Escaneo", "Descubre puertos abiertos y servicios.")
add_mod(32, 4, "Escaneos Sigilosos (Stealth)", "Evade firewalls y sistemas de detección.")
add_mod(33, 4, "Fingerprinting de SO", "Identifica qué sistema operativo usa la víctima.")
add_mod(34, 4, "Scripts NSE de Nmap", "Automatiza la detección de vulnerabilidades.")
add_mod(35, 4, "Masscan: Velocidad Extrema", "Escanea todo internet en minutos.")
add_mod(36, 4, "Enumeración SMB y NetBIOS", "Explora redes Windows compartidas.")
add_mod(37, 4, "Enumeración SNMP", "Extrae datos de routers e impresoras.")
add_mod(38, 4, "Detección de WAF e IPS", "Identifica las defensas del enemigo.")
add_mod(39, 4, "Mapeo de Red con Zenmap", "Visualiza la topología de la red.")
add_mod(40, 4, "Escáneres de Vulnerabilidades", "Introducción a Nessus y OpenVAS.")

# --- NIVEL 5: VULNERABILIDADES ---
add_mod(41, 5, "Conceptos de Exploits y Payloads", "Entiende cómo funciona un ataque.")
add_mod(42, 5, "Searchsploit: Base de Datos", "Encuentra exploits para cualquier versión.")
add_mod(43, 5, "Buffer Overflow Básico", "Desborda la memoria para inyectar código.")
add_mod(44, 5, "Inyección SQL (SQLi)", "Roba bases de datos enteras desde la web.")
add_mod(45, 5, "Cross-Site Scripting (XSS)", "Ejecuta scripts en el navegador de la víctima.")
add_mod(46, 5, "Ejecución Remota (RCE)", "El santo grial: toma control del servidor.")
add_mod(47, 5, "Inclusión de Archivos (LFI/RFI)", "Lee archivos sensibles del servidor.")
add_mod(48, 5, "Fuerza Bruta con Hydra", "Rompe contraseñas de SSH, FTP y Web.")
add_mod(49, 5, "Ataques de Diccionario", "Usa wordlists optimizadas como Rockyou.")
add_mod(50, 5, "Análisis de Tráfico con Wireshark", "Intercepta y lee paquetes en la red.")

# --- NIVEL 6: METASPLOIT ---
add_mod(51, 6, "Arquitectura de Metasploit", "Domina el framework más poderoso.")
add_mod(52, 6, "Selección de Exploits", "Elige el arma correcta para el objetivo.")
add_mod(53, 6, "Configuración de Payloads", "Reverse Shells vs Bind Shells.")
add_mod(54, 6, "Meterpreter: La Shell Mágica", "Comandos avanzados post-explotación.")
add_mod(55, 6, "Msfvenom: Creación de Troyanos", "Genera backdoors indetectables.")
add_mod(56, 6, "Persistencia en el Sistema", "Asegura tu acceso para siempre.")
add_mod(57, 6, "Pivoting: Saltando entre Redes", "Usa una máquina hackeada para atacar otras.")
add_mod(58, 6, "Módulos Auxiliares", "Escaneo y fuzzing desde Metasploit.")
add_mod(59, 6, "Armitage: Hacking Gráfico", "Gestiona equipos de ataque visualmente.")
add_mod(60, 6, "Evasión de Antivirus Básica", "Técnicas de ofuscación de payloads.")

# --- NIVEL 7: INGENIERÍA SOCIAL ---
add_mod(61, 7, "Psicología del Engaño", "Manipula la mente humana.")
add_mod(62, 7, "Phishing de Credenciales", "Clona sitios web para robar passwords.")
add_mod(63, 7, "Spear Phishing Dirigido", "Ataques personalizados de alta precisión.")
add_mod(64, 7, "Social Engineering Toolkit (SET)", "Automatiza tus campañas de engaño.")
add_mod(65, 7, "Creación de Payloads Maliciosos", "Archivos PDF y Word infectados.")
add_mod(66, 7, "Vishing y Smishing", "Ataques por voz y SMS.")
add_mod(67, 7, "USB Drops: El Caballo de Troya", "Ataques físicos con pendrives.")
add_mod(68, 7, "Pretexting y Escenarios", "Crea historias creíbles para tus víctimas.")
add_mod(69, 7, "OSINT para Ingeniería Social", "Usa datos personales para ganar confianza.")
add_mod(70, 7, "Defensa contra Ingeniería Social", "Cómo entrenar a usuarios para no caer.")

# --- NIVEL 8: CRIPTOGRAFÍA ---
add_mod(71, 8, "Historia de la Criptografía", "De César a Enigma y más allá.")
add_mod(72, 8, "Hashes vs Encriptación", "Diferencias clave y usos.")
add_mod(73, 8, "Identificación de Hashes", "Reconoce MD5, SHA1, NTLM, etc.")
add_mod(74, 8, "John the Ripper", "El destripador de contraseñas clásico.")
add_mod(75, 8, "Hashcat: Poder de la GPU", "Cracking de alta velocidad.")
add_mod(76, 8, "Ataques de Rainbow Tables", "Usa tablas precalculadas para velocidad.")
add_mod(77, 8, "Esteganografía", "Oculta mensajes dentro de imágenes.")
add_mod(78, 8, "Cifrado Asimétrico (RSA)", "Claves públicas y privadas.")
add_mod(79, 8, "Certificados SSL/TLS", "Seguridad en la web.")
add_mod(80, 8, "Cracking de Archivos Zip/PDF", "Rompe la seguridad de documentos.")

# --- NIVEL 9: POST-EXPLOTACIÓN ---
add_mod(81, 9, "Escalada de Privilegios (Linux)", "De usuario normal a Root.")
add_mod(82, 9, "Escalada de Privilegios (Windows)", "De usuario a System Administrator.")
add_mod(83, 9, "Extracción de Credenciales (Mimikatz)", "Roba contraseñas de la memoria.")
add_mod(84, 9, "Keyloggers", "Registra cada tecla pulsada.")
add_mod(85, 9, "Movimiento Lateral", "Muévete por la red corporativa.")
add_mod(86, 9, "Data Exfiltration", "Saca los datos robados sin ser detectado.")
add_mod(87, 9, "Backdoors Persistentes", "Mantén la puerta trasera abierta.")
add_mod(88, 9, "Borrado de Evidencias Avanzado", "Técnicas anti-forenses.")
add_mod(89, 9, "Rootkits", "Malware invisible en el kernel.")
add_mod(90, 9, "Golden Ticket Attack", "Control total del dominio Windows.")

# --- NIVEL 10: DIOS DEL ROOT ---
add_mod(91, 10, "Hacking de Redes Wi-Fi (Aircrack-ng)", "Rompe WPA2 y WPA3.")
add_mod(92, 10, "Ataques Man-in-the-Middle", "Intercepta comunicaciones en tiempo real.")
add_mod(93, 10, "Hacking de Aplicaciones Web (OWASP)", "Domina el Top 10 de vulnerabilidades.")
add_mod(94, 10, "Burp Suite Profesional", "La herramienta definitiva para web hacking.")
add_mod(95, 10, "Hacking Móvil (Android/iOS)", "Auditoría de apps y dispositivos.")
add_mod(96, 10, "Ingeniería Inversa Básica", "Desensambla programas para ver cómo funcionan.")
add_mod(97, 10, "Exploit Development (Buffer Overflow)", "Escribe tus propios exploits desde cero.")
add_mod(98, 10, "Hacking de Infraestructuras Cloud", "AWS, Azure y Google Cloud.")
add_mod(99, 10, "Red Teaming vs Blue Teaming", "Simulaciones de guerra cibernética real.")
add_mod(100, 10, "El Camino del CISO", "Cómo convertirte en Director de Seguridad.")
