"""
Contenido de los Laboratorios Prácticos (Simulador de Hacking).
Categorías: Redes, Web, Criptografía, Forense, Linux.
"""

LAB_CATEGORIES = {
    "network": "🌐 Hacking de Redes",
    "web": "🌍 Hacking Web",
    "crypto": "🔐 Criptografía",
    "linux": "🐧 Linux & Bash",
    "forensics": "🕵️‍♂️ Forense Digital"
}

# Estructura del Laboratorio
# id: int
# cat: category key
# title: str
# mission: str (Briefing)
# command: str (Simulated command)
# output: str (Simulated terminal output)
# question: str (Challenge)
# flag: str (Correct answer)
# xp: int
# premium: bool

LABS = {}

def add_lab(id, cat, title, mission, command, output, question, flag, xp=100, premium=True):
    LABS[id] = {
        "cat": cat,
        "title": title,
        "mission": mission,
        "command": command,
        "output": output,
        "question": question,
        "flag": flag,
        "xp": xp,
        "premium": premium
    }

# --- 🐧 LINUX BASICS (GRATIS) ---
add_lab(1, "linux", "Reconocimiento de Usuario", 
    "Acabas de obtener acceso a una shell básica. Tu primera tarea es identificar quién eres en el sistema.",
    "whoami && id",
    "root\nuid=0(root) gid=0(root) groups=0(root)",
    "¿Cuál es el UID del usuario actual?",
    "0",
    xp=50, premium=False)

add_lab(2, "linux", "Buscando Archivos Ocultos", 
    "Hay un archivo confidencial oculto en el directorio actual. Encuéntralo.",
    "ls -la",
    "drwxr-xr-x  2 root root 4096 Dec 1 10:00 .\ndrwxr-xr-x 10 root root 4096 Dec 1 09:00 ..\n-rw-r--r--  1 root root  120 Dec 1 10:01 .secret_config",
    "¿Cuál es el nombre del archivo oculto encontrado?",
    ".secret_config",
    xp=50, premium=False)

add_lab(3, "linux", "Leyendo Contenidos", 
    "Necesitamos leer el contenido del archivo 'password.txt'.",
    "cat password.txt",
    "User: admin\nPass: SuperSecureP@ss123!",
    "¿Cuál es la contraseña que aparece en el archivo?",
    "SuperSecureP@ss123!",
    xp=50, premium=False)

# --- 🌐 NETWORK HACKING (PREMIUM) ---
add_lab(4, "network", "Escaneo de Puertos Básico", 
    "El objetivo es el servidor 192.168.1.55. Descubre qué servicios web están corriendo.",
    "nmap -p 80,443 192.168.1.55",
    "PORT    STATE SERVICE\n80/tcp  open  http\n443/tcp closed https",
    "¿Qué puerto TCP está ABIERTO (open)?",
    "80",
    xp=100, premium=True)

add_lab(5, "network", "Identificación de Versiones", 
    "Necesitamos saber la versión exacta del servidor FTP para buscar exploits.",
    "nmap -sV -p 21 10.10.10.5",
    "PORT   STATE SERVICE VERSION\n21/tcp open  ftp     vsftpd 2.3.4",
    "¿Cuál es la versión exacta del servicio vsftpd?",
    "2.3.4",
    xp=100, premium=True)

add_lab(6, "network", "Detectando Sistema Operativo", 
    "Identifica el sistema operativo del objetivo basándote en el TTL del ping.",
    "ping -c 1 192.168.1.100",
    "64 bytes from 192.168.1.100: icmp_seq=1 ttl=128 time=0.4 ms",
    "Basado en el TTL=128, ¿es el sistema 'Windows' o 'Linux'?",
    "Windows",
    xp=100, premium=True)

# --- 🌍 WEB HACKING (PREMIUM) ---
add_lab(7, "web", "Buscando Directorios Ocultos", 
    "Usa Gobuster para encontrar paneles de administración ocultos en el sitio web.",
    "gobuster dir -u http://target.com -w common.txt",
    "/index.php (Status: 200)\n/images (Status: 301)\n/admin (Status: 200)\n/login (Status: 200)",
    "¿Cuál es la ruta del panel de administración encontrado?",
    "/admin",
    xp=150, premium=True)

add_lab(8, "web", "Inyección SQL (SQLi)", 
    "Hemos probado una comilla simple (') en el parámetro ID. Analiza el error.",
    "GET /product.php?id=1'",
    "Error: You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version...",
    "¿Es vulnerable este parámetro a SQL Injection? (Si/No)",
    "Si",
    xp=150, premium=True)

add_lab(9, "web", "Robando Base de Datos", 
    "Usamos SQLMap para extraer las tablas de la base de datos.",
    "sqlmap -u 'http://target.com?id=1' --dbs",
    "available databases [2]:\n[*] information_schema\n[*] users_db",
    "¿Cuál es el nombre de la base de datos de usuarios?",
    "users_db",
    xp=150, premium=True)

add_lab(10, "web", "Cross-Site Scripting (XSS)", 
    "Encontramos un campo de comentarios sin sanitizar. ¿Qué payload usarías para probar un XSS básico?",
    "Input Testing...",
    "Payload sugerido: <script>alert(1)</script>",
    "Escribe el payload clásico de alerta javascript.",
    "<script>alert(1)</script>",
    xp=150, premium=True)

# --- 🔐 CRIPTOGRAFÍA (PREMIUM) ---
add_lab(11, "crypto", "Decodificando Base64", 
    "Interceptamos este string extraño: 'SGFja2VkIQ=='. ¿Qué significa?",
    "echo 'SGFja2VkIQ==' | base64 -d",
    "Hacked!",
    "¿Cuál es el mensaje oculto?",
    "Hacked!",
    xp=100, premium=True)

add_lab(12, "crypto", "Rompiendo Hashes MD5", 
    "Tenemos el hash MD5 del admin: '5f4dcc3b5aa765d61d8327deb882cf99'. Úsalo contra rockyou.txt.",
    "hashcat -m 0 5f4dcc3b5aa765d61d8327deb882cf99 rockyou.txt",
    "5f4dcc3b5aa765d61d8327deb882cf99:password",
    "¿Cuál es la contraseña en texto plano?",
    "password",
    xp=200, premium=True)

add_lab(13, "crypto", "Identificando Hashes", 
    "Analiza este hash: $1$O3JMY.Tw$AdLnLjQ/5jXF9.MTKp.S0.",
    "hash-identifier '$1$O3JMY.Tw$AdLnLjQ/5jXF9.MTKp.S0.'",
    "Possible Hashs:\n[+] MD5 (Unix)\n[+] MD5 (APR)",
    "¿Qué tipo de algoritmo de hash es (formato Unix)?",
    "MD5",
    xp=100, premium=True)

# --- 🕵️‍♂️ FORENSE (PREMIUM) ---
add_lab(14, "forensics", "Metadatos de Imagen", 
    "Analiza la foto 'evidence.jpg' para ver quién la tomó.",
    "exiftool evidence.jpg",
    "File Name: evidence.jpg\nCamera Model: iPhone 13\nArtist: John Doe\nGPS Position: 40.7128 N, 74.0060 W",
    "¿Quién aparece como el 'Artist' en los metadatos?",
    "John Doe",
    xp=150, premium=True)

add_lab(15, "forensics", "Análisis de Strings", 
    "Hay un ejecutable sospechoso 'malware.exe'. Busca cadenas de texto legibles dentro.",
    "strings malware.exe | grep http",
    "http://evil-server.com/payload.exe\nhttp://google.com",
    "¿Cuál es el dominio del servidor malicioso (evil)?",
    "evil-server.com",
    xp=150, premium=True)
