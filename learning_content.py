"""
Contenido estático para la Ruta de Aprendizaje de Kali Linux.
Este contenido es exclusivo para usuarios Premium.
"""

MODULES = {
    1: {
        "title": "Introducción a Kali Linux y Ética Hacking",
        "description": "Conceptos básicos, legalidad y configuración del entorno.",
        "content": (
            "<b>MÓDULO 1: INTRODUCCIÓN</b>\n\n"
            "Bienvenido al mundo del Hacking Ético. Antes de tocar una terminal, debes entender las reglas del juego.\n\n"
            "<b>1. ¿Qué es Kali Linux?</b>\n"
            "Kali es una distribución de Linux basada en Debian, diseñada específicamente para auditorías de seguridad y pruebas de penetración. Viene con cientos de herramientas preinstaladas.\n\n"
            "<b>2. Tipos de Hackers:</b>\n"
            "🎩 <b>White Hat:</b> Hackers éticos que buscan vulnerabilidades para arreglarlas (Tú).\n"
            "🎩 <b>Black Hat:</b> Ciberdelincuentes que buscan dañar o robar.\n"
            "🎩 <b>Grey Hat:</b> Un punto medio, a veces actúan sin permiso pero sin mala intención.\n\n"
            "<b>3. La Regla de Oro:</b>\n"
            "⚠️ <b>NUNCA</b> ataques un sistema sin permiso explícito y por escrito. Eso es ilegal. Practica solo en tus propios laboratorios o entornos controlados.\n\n"
            "<b>4. Tu Primera Misión:</b>\n"
            "Instala Kali Linux en una Máquina Virtual (VirtualBox o VMware). Asegúrate de que la red esté en modo 'NAT' para tener internet."
        )
    },
    2: {
        "title": "La Terminal de Linux (Comandos Básicos)",
        "description": "Domina la línea de comandos, la herramienta principal del hacker.",
        "content": (
            "<b>MÓDULO 2: LA TERMINAL</b>\n\n"
            "La interfaz gráfica es para usuarios normales. Los hackers viven en la terminal.\n\n"
            "<b>Comandos Esenciales:</b>\n\n"
            "🔹 <code>pwd</code>: (Print Working Directory) Te dice en qué carpeta estás.\n"
            "🔹 <code>ls</code>: Lista los archivos de la carpeta actual. Usa <code>ls -la</code> para ver archivos ocultos y permisos.\n"
            "🔹 <code>cd [carpeta]</code>: (Change Directory) Para entrar a una carpeta. <code>cd ..</code> para retroceder.\n"
            "🔹 <code>mkdir [nombre]</code>: Crea una nueva carpeta.\n"
            "🔹 <code>touch [archivo]</code>: Crea un archivo vacío.\n"
            "🔹 <code>cat [archivo]</code>: Muestra el contenido de un archivo en pantalla.\n\n"
            "<b>Ejercicio:</b>\n"
            "Abre tu terminal, crea una carpeta llamada 'Hacking101', entra en ella y crea un archivo llamado 'notas.txt'."
        )
    },
    3: {
        "title": "Sistema de Archivos y Permisos",
        "description": "Entiende cómo Linux organiza los datos y quién puede tocarlos.",
        "content": (
            "<b>MÓDULO 3: PERMISOS Y FICHEROS</b>\n\n"
            "En Linux, todo es un archivo. Y cada archivo tiene un dueño.\n\n"
            "<b>Estructura Básica:</b>\n"
            "📂 <code>/</code>: La raíz (Root) del sistema.\n"
            "📂 <code>/home</code>: Donde viven los usuarios (como 'Mis Documentos').\n"
            "📂 <code>/etc</code>: Archivos de configuración del sistema.\n"
            "📂 <code>/bin</code> y <code>/usr/bin</code>: Donde están los programas (comandos).\n\n"
            "<b>Permisos (rwx):</b>\n"
            "Cada archivo tiene permisos para: <b>U</b>suario (dueño), <b>G</b>rupo y <b>O</b>tros.\n"
            "🔸 <b>r</b> (read): Leer.\n"
            "🔸 <b>w</b> (write): Escribir/Modificar.\n"
            "🔸 <b>x</b> (execute): Ejecutar (como programa).\n\n"
            "<b>Comando chmod:</b>\n"
            "<code>chmod +x script.sh</code> (Da permiso de ejecución).\n"
            "<code>chmod 777 archivo</code> (Da TODOS los permisos a TODOS - ¡Peligroso!)."
        )
    },
    4: {
        "title": "Gestión de Usuarios y Procesos",
        "description": "Controla quién entra y qué se está ejecutando.",
        "content": (
            "<b>MÓDULO 4: USUARIOS Y PROCESOS</b>\n\n"
            "<b>El Superusuario (Root):</b>\n"
            "Es el dios del sistema. Puede hacer todo. En Kali, a menudo trabajamos como root o usamos <code>sudo</code> para pedir sus poderes temporalmente.\n\n"
            "🔹 <code>sudo [comando]</code>: Ejecuta el comando como administrador.\n"
            "🔹 <code>sudo su</code>: Te convierte en root permanentemente (hasta que escribas <code>exit</code>).\n\n"
            "<b>Gestión de Procesos:</b>\n"
            "🔹 <code>top</code> o <code>htop</code>: Muestra los programas corriendo en tiempo real (como el Administrador de Tareas).\n"
            "🔹 <code>ps aux</code>: Lista todos los procesos activos.\n"
            "🔹 <code>kill [PID]</code>: Cierra un proceso forzosamente usando su ID (PID)."
        )
    },
    5: {
        "title": "Fundamentos de Redes para Hackers",
        "description": "IPs, Puertos, TCP/UDP y el modelo OSI.",
        "content": (
            "<b>MÓDULO 5: REDES BÁSICAS</b>\n\n"
            "No puedes hackear una red si no sabes cómo funciona.\n\n"
            "<b>Conceptos Clave:</b>\n"
            "🌐 <b>Dirección IP:</b> La identificación de una máquina (ej. 192.168.1.5).\n"
            "🌐 <b>MAC Address:</b> La identificación física de la tarjeta de red.\n"
            "🌐 <b>Puerto:</b> Una 'puerta' para un servicio específico (ej. Puerto 80 es Web/HTTP, Puerto 22 es SSH).\n\n"
            "<b>Protocolos:</b>\n"
            "🔸 <b>TCP:</b> Fiable, verifica que los datos lleguen (ej. cargar una web).\n"
            "🔸 <b>UDP:</b> Rápido, no verifica (ej. streaming de video).\n\n"
            "<b>Herramientas:</b>\n"
            "🔹 <code>ifconfig</code> o <code>ip a</code>: Ver tu configuración de red.\n"
            "🔹 <code>ping [destino]</code>: Ver si una máquina está viva."
        )
    },
    6: {
        "title": "Anonimato y Privacidad",
        "description": "Cómo proteger tu identidad. Tor, VPN y Proxychains.",
        "content": (
            "<b>MÓDULO 6: ANONIMATO</b>\n\n"
            "Antes de investigar, protégete.\n\n"
            "<b>Herramientas de Privacidad:</b>\n\n"
            "🕵️‍♂️ <b>VPN (Virtual Private Network):</b> Cifra tu tráfico y cambia tu IP. Es la capa básica de seguridad.\n\n"
            "🧅 <b>Tor (The Onion Router):</b> Rebota tu conexión por varios nodos voluntarios alrededor del mundo. Muy lento, pero muy anónimo.\n\n"
            "🔗 <b>Proxychains:</b> Una herramienta de Kali que permite forzar a cualquier programa a usar una cadena de proxies o Tor.\n"
            "Uso: <code>proxychains firefox</code> (Abre el navegador a través de proxies).\n\n"
            "<b>Cambiar tu MAC:</b>\n"
            "<code>macchanger -r eth0</code> (Asigna una dirección MAC aleatoria a tu tarjeta de red para no ser rastreado físicamente)."
        )
    },
    7: {
        "title": "Recolección de Información (OSINT)",
        "description": "Investigación de fuentes abiertas. Google Dorks y TheHarvester.",
        "content": (
            "<b>MÓDULO 7: OSINT (Open Source Intelligence)</b>\n\n"
            "El 90% del hacking es recolección de información. Saber es poder.\n\n"
            "<b>Google Dorks:</b>\n"
            "Uso avanzado del buscador para encontrar cosas ocultas.\n"
            "🔹 <code>site:objetivo.com filetype:pdf</code> (Busca PDFs en ese dominio).\n"
            "🔹 <code>intitle:\"index of\"</code> (Busca directorios abiertos).\n\n"
            "<b>Herramientas en Kali:</b>\n"
            "🔹 <b>TheHarvester:</b> Busca emails, subdominios y nombres de empleados en Google, LinkedIn, etc.\n"
            "   Uso: <code>theHarvester -d objetivo.com -b google</code>\n\n"
            "🔹 <b>Whois:</b> Te dice quién registró un dominio.\n"
            "   Uso: <code>whois objetivo.com</code>"
        )
    },
    8: {
        "title": "Escaneo de Vulnerabilidades (Nmap)",
        "description": "El rey de los escáneres. Descubre puertos y servicios.",
        "content": (
            "<b>MÓDULO 8: ESCANEO CON NMAP</b>\n\n"
            "Nmap es la herramienta más importante que aprenderás. Sirve para ver qué 'puertas' (puertos) están abiertas en un objetivo.\n\n"
            "<b>Escaneos Básicos:</b>\n"
            "🔹 <code>nmap 192.168.1.1</code>: Escaneo rápido de puertos comunes.\n"
            "🔹 <code>nmap -sV 192.168.1.1</code>: Detecta la VERSIÓN de los servicios (útil para buscar vulnerabilidades).\n"
            "🔹 <code>nmap -O 192.168.1.1</code>: Intenta adivinar el Sistema Operativo.\n"
            "🔹 <code>nmap -A 192.168.1.1</code>: Escaneo agresivo (todo lo anterior + scripts).\n\n"
            "<b>Interpretación:</b>\n"
            "Si ves <code>21/tcp open ftp vsftpd 2.3.4</code>, sabes que hay un servidor FTP versión 2.3.4. ¡Esa versión específica podría tener un fallo conocido!"
        )
    },
    9: {
        "title": "Introducción a Metasploit",
        "description": "Framework de explotación. Payloads y Exploits.",
        "content": (
            "<b>MÓDULO 9: METASPLOIT</b>\n\n"
            "Metasploit es una navaja suiza para lanzar exploits (código que aprovecha una vulnerabilidad).\n\n"
            "<b>Estructura:</b>\n"
            "🚀 <b>Exploit:</b> El código que rompe la seguridad.\n"
            "📦 <b>Payload:</b> Lo que se ejecuta una vez dentro (ej. tomar control remoto).\n\n"
            "<b>Uso Básico (msfconsole):</b>\n"
            "1. <code>msfconsole</code> (Inicia el programa).\n"
            "2. <code>search [nombre]</code> (Busca un exploit, ej. 'vsftpd').\n"
            "3. <code>use [ruta_del_exploit]</code> (Selecciona el exploit).\n"
            "4. <code>set RHOSTS [ip_objetivo]</code> (Configura a quién atacar).\n"
            "5. <code>run</code> o <code>exploit</code> (¡Fuego!)."
        )
    },
    10: {
        "title": "Reporte y Documentación",
        "description": "Cómo presentar tus hallazgos profesionalmente.",
        "content": (
            "<b>MÓDULO 10: REPORTES</b>\n\n"
            "Si no lo documentas, no sucedió. En el hacking ético, el producto final es el REPORTE, no el hackeo.\n\n"
            "<b>Estructura de un Buen Reporte:</b>\n"
            "📄 <b>Resumen Ejecutivo:</b> Para los jefes (sin tecnicismos). 'Encontramos 3 fallos críticos que permiten robar datos'.\n"
            "📄 <b>Detalles Técnicos:</b> Para los informáticos. Paso a paso de cómo replicar el fallo.\n"
            "📄 <b>Impacto:</b> ¿Qué pasaría si un criminal explota esto?\n"
            "📄 <b>Remediación:</b> ¿Cómo se arregla? (Parches, configuración, código).\n\n"
            "<b>¡FELICIDADES!</b> Has completado la ruta básica. Ahora eres un Iniciado en Kali Linux."
        )
    }
}
