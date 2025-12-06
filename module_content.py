"""
Contenido HTML detallado para cada uno de los 100 módulos del sistema de aprendizaje.
Este contenido se renderiza en la mini app web para usuarios premium.
"""

# Diccionario con contenido extendido para cada módulo
# Clave: module_id, Valor: dict con 'objectives', 'concepts', 'tools'

MODULE_CONTENT = {
    # NIVEL 1: GÉNESIS DEL HACKER
    1: {
        "objectives": ["Descargar e instalar Kali Linux", "Configurar una máquina virtual", "Realizar la primera actualización del sistema"],
        "concepts": ["Distribución Linux", "Máquina Virtual", "Hipervisor"],
        "tools": ["VirtualBox", "VMware", "apt"]
    },
    2: {
        "objectives": ["Navegar por el sistema de archivos", "Ejecutar comandos básicos", "Entender el prompt de comandos"],
        "concepts": ["Shell", "Bash", "Terminal"],
        "tools": ["cd", "ls", "pwd", "cat"]
    },
    3: {
        "objectives": ["Entender el concepto de root", "Usar sudo correctamente", "Gestionar permisos de usuario"],
        "concepts": ["Root", "Sudo", "Privilegios"],
        "tools": ["sudo", "su", "chmod", "chown"]
    },
    4: {
        "objectives": ["Conocer la estructura de directorios", "Ubicar archivos importantes", "Entender /etc, /home, /var"],
        "concepts": ["FHS", "Directorios", "Particiones"],
        "tools": ["tree", "find", "locate"]
    },
    5: {
        "objectives": ["Entender direcciones IP", "Conocer los puertos comunes", "Identificar protocolos básicos"],
        "concepts": ["TCP/IP", "Puertos", "Protocolos"],
        "tools": ["ifconfig", "ip", "netstat"]
    },
    6: {
        "objectives": ["Crear un entorno aislado", "Configurar redes virtuales", "Practicar sin riesgos legales"],
        "concepts": ["Sandbox", "NAT", "Bridged Network"],
        "tools": ["VirtualBox", "Docker", "Vagrant"]
    },
    7: {
        "objectives": ["Dominar comandos esenciales", "Manipular archivos y texto", "Automatizar tareas simples"],
        "concepts": ["Pipes", "Redirección", "Wildcards"],
        "tools": ["grep", "awk", "sed", "cut"]
    },
    8: {
        "objectives": ["Editar archivos de configuración", "Usar atajos de teclado", "Personalizar el editor"],
        "concepts": ["Modo inserción", "Modo comando", "Buffers"],
        "tools": ["nano", "vim", "vi"]
    },
    9: {
        "objectives": ["Escribir scripts básicos", "Usar variables y bucles", "Automatizar tareas repetitivas"],
        "concepts": ["Variables", "Loops", "Funciones"],
        "tools": ["bash", "chmod +x", "cron"]
    },
    10: {
        "objectives": ["Conocer las leyes de hacking", "Entender el hacking ético", "Obtener permisos antes de auditar"],
        "concepts": ["White Hat", "Pentesting Legal", "Scope"],
        "tools": ["Contratos", "NDA", "Metodologías"]
    },
    # NIVEL 2: FANTASMA EN LA RED
    11: {
        "objectives": ["Configurar una VPN", "Entender el cifrado de tráfico", "Elegir un proveedor seguro"],
        "concepts": ["Tunneling", "OpenVPN", "WireGuard"],
        "tools": ["openvpn", "wireguard", "protonvpn"]
    },
    12: {
        "objectives": ["Instalar y usar Tor Browser", "Entender la red Onion", "Navegar de forma anónima"],
        "concepts": ["Circuitos", "Exit Nodes", "Hidden Services"],
        "tools": ["tor", "torbrowser", "onionshare"]
    },
    13: {
        "objectives": ["Configurar proxychains", "Encadenar múltiples proxies", "Ocultar tu origen"],
        "concepts": ["SOCKS", "HTTP Proxy", "Chain Types"],
        "tools": ["proxychains", "proxychains-ng"]
    },
    14: {
        "objectives": ["Cambiar tu dirección MAC", "Evitar filtros de red", "Mantener el anonimato local"],
        "concepts": ["MAC Address", "ARP", "NIC"],
        "tools": ["macchanger", "ifconfig"]
    },
    15: {
        "objectives": ["Configurar Firefox para privacidad", "Bloquear trackers", "Usar extensiones de seguridad"],
        "concepts": ["Fingerprinting", "Cookies", "WebRTC"],
        "tools": ["uBlock Origin", "Privacy Badger", "NoScript"]
    },
    16: {
        "objectives": ["Generar claves PGP", "Firmar y cifrar mensajes", "Verificar identidades"],
        "concepts": ["Criptografía asimétrica", "Firma digital", "Web of Trust"],
        "tools": ["gpg", "kleopatra", "thunderbird"]
    },
    17: {
        "objectives": ["Identificar archivos de log", "Borrar rastros de actividad", "Usar herramientas anti-forenses"],
        "concepts": ["Logs", "Syslog", "Timestamps"],
        "tools": ["shred", "wipe", "bleachbit"]
    },
    18: {
        "objectives": ["Instalar y usar Tails", "Entender el sistema amnésico", "Usar almacenamiento persistente"],
        "concepts": ["Live OS", "Amnesia", "Persistent Volume"],
        "tools": ["Tails", "USB booteable"]
    },
    19: {
        "objectives": ["Entender Bitcoin y Monero", "Usar wallets anónimas", "Mezclar criptomonedas"],
        "concepts": ["Blockchain", "Anonimato", "Mixing"],
        "tools": ["Electrum", "Monero CLI", "Wasabi"]
    },
    20: {
        "objectives": ["Desarrollar mentalidad de seguridad", "Proteger tu identidad", "Evitar errores comunes"],
        "concepts": ["OPSEC", "Compartimentación", "Minimal Footprint"],
        "tools": ["Buenas prácticas", "Checklist OPSEC"]
    },
    # NIVEL 3: OJOS QUE TODO LO VEN
    21: {
        "objectives": ["Dominar operadores de Google", "Encontrar información sensible", "Automatizar búsquedas"],
        "concepts": ["Dorks", "Operadores", "Indexación"],
        "tools": ["Google", "DuckDuckGo", "GHDB"]
    },
    22: {
        "objectives": ["Recolectar emails", "Encontrar subdominios", "Mapear infraestructura"],
        "concepts": ["Enumeración", "APIs", "Fuentes públicas"],
        "tools": ["theHarvester", "recon-ng"]
    },
    23: {
        "objectives": ["Buscar dispositivos expuestos", "Identificar vulnerabilidades IoT", "Analizar resultados"],
        "concepts": ["IoT", "Banners", "Fingerprinting"],
        "tools": ["Shodan", "Censys", "ZoomEye"]
    },
    24: {
        "objectives": ["Crear grafos de relaciones", "Investigar objetivos", "Conectar entidades"],
        "concepts": ["Grafos", "Entidades", "Transformaciones"],
        "tools": ["Maltego", "Maltego CE"]
    },
    25: {
        "objectives": ["Extraer metadatos de archivos", "Analizar fotos y documentos", "Encontrar información oculta"],
        "concepts": ["EXIF", "Metadatos", "Geolocalización"],
        "tools": ["exiftool", "metagoofil", "FOCA"]
    },
    26: {
        "objectives": ["Enumerar registros DNS", "Descubrir subdominios", "Identificar servidores"],
        "concepts": ["A", "MX", "NS", "CNAME", "TXT"],
        "tools": ["dig", "nslookup", "dnsrecon", "dnsenum"]
    },
    27: {
        "objectives": ["Investigar perfiles sociales", "Correlacionar información", "Usar herramientas automatizadas"],
        "concepts": ["Username search", "Social footprint", "Digital presence"],
        "tools": ["sherlock", "social-analyzer", "holehe"]
    },
    28: {
        "objectives": ["Analizar versiones antiguas de sitios", "Encontrar información eliminada", "Usar archivos históricos"],
        "concepts": ["Web Archive", "Snapshots", "Cache"],
        "tools": ["Wayback Machine", "archive.org", "CachedView"]
    },
    29: {
        "objectives": ["Diferenciar técnicas de escaneo", "Elegir el método correcto", "Evitar detección"],
        "concepts": ["Footprinting", "Detección", "Ruido de red"],
        "tools": ["whois", "nmap -sn"]
    },
    30: {
        "objectives": ["Organizar información recolectada", "Crear informes", "Preparar el ataque"],
        "concepts": ["Intelligence", "Reportes", "Análisis"],
        "tools": ["CherryTree", "Notion", "ObsidianMD"]
    },
    # NIVEL 4: EL ARTE DE LA INTRUSIÓN
    31: {
        "objectives": ["Realizar escaneos de puertos", "Detectar servicios", "Interpretar resultados"],
        "concepts": ["TCP", "UDP", "Estados de puertos"],
        "tools": ["nmap", "zenmap"]
    },
    32: {
        "objectives": ["Evitar detección por IDS", "Usar técnicas sigilosas", "Fragmentar paquetes"],
        "concepts": ["SYN Scan", "FIN Scan", "Decoys"],
        "tools": ["nmap -sS", "nmap -sN", "nmap -D"]
    },
    33: {
        "objectives": ["Identificar sistemas operativos", "Analizar TTL y ventanas", "Usar detección pasiva"],
        "concepts": ["TCP/IP Stack", "Fingerprint", "Banner Grabbing"],
        "tools": ["nmap -O", "p0f", "xprobe2"]
    },
    34: {
        "objectives": ["Usar scripts NSE", "Detectar vulnerabilidades", "Automatizar reconocimiento"],
        "concepts": ["Lua", "Categories", "Scripts"],
        "tools": ["nmap --script", "nmap -sC"]
    },
    35: {
        "objectives": ["Escanear rangos masivos", "Optimizar velocidad", "Procesar resultados"],
        "concepts": ["Rate limiting", "SYN packets", "Output formats"],
        "tools": ["masscan", "RustScan"]
    },
    36: {
        "objectives": ["Enumerar recursos compartidos", "Identificar usuarios", "Explotar SMB"],
        "concepts": ["SMB", "NetBIOS", "Null Sessions"],
        "tools": ["smbclient", "enum4linux", "crackmapexec"]
    },
    37: {
        "objectives": ["Extraer información SNMP", "Usar community strings", "Enumerar dispositivos"],
        "concepts": ["OIDs", "MIBs", "Community strings"],
        "tools": ["snmpwalk", "onesixtyone", "snmp-check"]
    },
    38: {
        "objectives": ["Identificar WAFs", "Evadir protecciones", "Detectar IPS"],
        "concepts": ["WAF", "IPS", "Rate limiting"],
        "tools": ["wafw00f", "nmap --script http-waf-detect"]
    },
    39: {
        "objectives": ["Visualizar topologías", "Crear mapas de red", "Documentar infraestructura"],
        "concepts": ["Network diagrams", "Topology", "Visualization"],
        "tools": ["Zenmap", "Nmap output", "draw.io"]
    },
    40: {
        "objectives": ["Usar escáneres automatizados", "Interpretar reportes", "Priorizar vulnerabilidades"],
        "concepts": ["CVSS", "CVE", "False positives"],
        "tools": ["Nessus", "OpenVAS", "Nikto"]
    },
    # NIVEL 5: ROMPIENDO MUROS
    41: {
        "objectives": ["Entender tipos de exploits", "Conocer payloads comunes", "Diferenciar técnicas"],
        "concepts": ["Buffer Overflow", "Shellcode", "ROP"],
        "tools": ["Metasploit", "ExploitDB"]
    },
    42: {
        "objectives": ["Buscar exploits conocidos", "Usar la base de datos", "Adaptar exploits"],
        "concepts": ["CVE", "PoC", "Exploit adaptation"],
        "tools": ["searchsploit", "exploitdb"]
    },
    43: {
        "objectives": ["Entender la memoria", "Identificar vulnerabilidades", "Crear exploits simples"],
        "concepts": ["Stack", "Heap", "EIP", "NOP sled"],
        "tools": ["gdb", "immunity debugger", "pattern_create"]
    },
    44: {
        "objectives": ["Detectar puntos de inyección", "Extraer datos de bases", "Automatizar ataques"],
        "concepts": ["UNION", "Blind SQLi", "Time-based"],
        "tools": ["sqlmap", "burpsuite"]
    },
    45: {
        "objectives": ["Inyectar código JavaScript", "Robar cookies", "Crear payloads"],
        "concepts": ["Reflected", "Stored", "DOM-based"],
        "tools": ["XSS Hunter", "BeEF"]
    },
    46: {
        "objectives": ["Identificar vulnerabilidades RCE", "Ejecutar comandos remotos", "Obtener shells"],
        "concepts": ["Command Injection", "Deserialization", "File Upload"],
        "tools": ["netcat", "reverse shells"]
    },
    47: {
        "objectives": ["Leer archivos del servidor", "Incluir archivos remotos", "Escalar a RCE"],
        "concepts": ["Path Traversal", "Wrappers", "Null bytes"],
        "tools": ["curl", "burpsuite"]
    },
    48: {
        "objectives": ["Atacar diferentes servicios", "Crear diccionarios efectivos", "Optimizar velocidad"],
        "concepts": ["Password spraying", "Credential stuffing"],
        "tools": ["hydra", "medusa", "ncrack"]
    },
    49: {
        "objectives": ["Generar wordlists", "Aplicar reglas", "Optimizar ataques"],
        "concepts": ["Rules", "Masks", "Combinator"],
        "tools": ["crunch", "cewl", "cupp"]
    },
    50: {
        "objectives": ["Capturar tráfico de red", "Analizar paquetes", "Filtrar información"],
        "concepts": ["Protocolos", "Filtros", "Dissectors"],
        "tools": ["wireshark", "tshark", "tcpdump"]
    },
    # NIVEL 6: MAESTRO DE MARIONETAS
    51: {
        "objectives": ["Entender la arquitectura", "Navegar módulos", "Usar workspace"],
        "concepts": ["Consola", "Módulos", "Database"],
        "tools": ["msfconsole", "msfdb"]
    },
    52: {
        "objectives": ["Buscar exploits adecuados", "Verificar compatibilidad", "Configurar opciones"],
        "concepts": ["RHOSTS", "RPORT", "Target"],
        "tools": ["search", "use", "info"]
    },
    53: {
        "objectives": ["Elegir el payload correcto", "Configurar listeners", "Entender staged vs stageless"],
        "concepts": ["Reverse shell", "Bind shell", "Encoders"],
        "tools": ["set PAYLOAD", "exploit"]
    },
    54: {
        "objectives": ["Navegar el sistema", "Elevar privilegios", "Persistencia básica"],
        "concepts": ["Channels", "Migration", "Post modules"],
        "tools": ["meterpreter commands"]
    },
    55: {
        "objectives": ["Generar ejecutables", "Crear payloads encodeados", "Usar diferentes formatos"],
        "concepts": ["Formats", "Templates", "Encoders"],
        "tools": ["msfvenom"]
    },
    56: {
        "objectives": ["Mantener acceso", "Crear backdoors", "Sobrevivir reinicios"],
        "concepts": ["Registry", "Services", "Scheduled tasks"],
        "tools": ["persistence modules"]
    },
    57: {
        "objectives": ["Saltar entre redes", "Configurar rutas", "Atacar subredes"],
        "concepts": ["Port forwarding", "SOCKS proxy", "Routes"],
        "tools": ["autoroute", "portfwd", "socks_proxy"]
    },
    58: {
        "objectives": ["Usar módulos de escaneo", "Realizar fuzzing", "Enumerar servicios"],
        "concepts": ["Scanner modules", "Fuzz testing"],
        "tools": ["auxiliary modules"]
    },
    59: {
        "objectives": ["Usar interfaz gráfica", "Gestionar múltiples targets", "Colaborar en equipo"],
        "concepts": ["GUI", "Sessions", "Visualization"],
        "tools": ["Armitage"]
    },
    60: {
        "objectives": ["Evitar detección básica", "Usar ofuscación", "Probar contra AV"],
        "concepts": ["Signatures", "Heuristics", "Sandbox"],
        "tools": ["Veil", "Shellter", "encoders"]
    },
    # NIVEL 7: INGENIERÍA SOCIAL OSCURA
    61: {
        "objectives": ["Entender la mente humana", "Usar principios de persuasión", "Explotar emociones"],
        "concepts": ["Cialdini", "Urgencia", "Autoridad"],
        "tools": ["Técnicas de manipulación"]
    },
    62: {
        "objectives": ["Clonar sitios web", "Capturar credenciales", "Analizar resultados"],
        "concepts": ["Credential harvesting", "Spoofing"],
        "tools": ["SET", "Gophish", "King Phisher"]
    },
    63: {
        "objectives": ["Investigar objetivos", "Personalizar ataques", "Maximizar efectividad"],
        "concepts": ["Reconnaissance", "Personalization", "Pretexting"],
        "tools": ["OSINT tools", "LinkedIn"]
    },
    64: {
        "objectives": ["Dominar SET", "Crear payloads", "Automatizar campañas"],
        "concepts": ["Attack vectors", "Website cloning"],
        "tools": ["setoolkit"]
    },
    65: {
        "objectives": ["Infectar documentos", "Usar macros maliciosas", "Evadir detección"],
        "concepts": ["Macros", "OLE", "Evasion"],
        "tools": ["macro_pack", "unicorn"]
    },
    66: {
        "objectives": ["Realizar llamadas de pretexto", "Enviar SMS maliciosos", "Combinar técnicas"],
        "concepts": ["Voice phishing", "SMS spoofing"],
        "tools": ["Caller ID spoofing", "SMS gateways"]
    },
    67: {
        "objectives": ["Preparar USB maliciosos", "Usar autorun", "Crear señuelos"],
        "concepts": ["Rubber Ducky", "BadUSB", "Drop locations"],
        "tools": ["USB Rubber Ducky", "Bash Bunny"]
    },
    68: {
        "objectives": ["Crear historias creíbles", "Mantener consistencia", "Ganar confianza"],
        "concepts": ["Role playing", "Backstory", "Props"],
        "tools": ["Planificación", "Documentación"]
    },
    69: {
        "objectives": ["Usar OSINT para SE", "Encontrar conexiones", "Personalizar ataques"],
        "concepts": ["Personal info", "Relationships", "Interests"],
        "tools": ["Maltego", "Social media"]
    },
    70: {
        "objectives": ["Crear conciencia de seguridad", "Detectar ataques", "Reportar incidentes"],
        "concepts": ["Security awareness", "Red flags", "Reporting"],
        "tools": ["Training programs", "Simulations"]
    },
    # NIVEL 8: CRIPTOGRAFÍA Y SECRETOS
    71: {
        "objectives": ["Conocer la historia", "Entender evolución", "Apreciar la importancia"],
        "concepts": ["Enigma", "DES", "AES"],
        "tools": ["Estudio histórico"]
    },
    72: {
        "objectives": ["Diferenciar hashing de cifrado", "Elegir el algoritmo correcto", "Verificar integridad"],
        "concepts": ["One-way", "Reversible", "Salt"],
        "tools": ["hashlib", "openssl"]
    },
    73: {
        "objectives": ["Identificar tipos de hash", "Usar herramientas de detección", "Preparar ataques"],
        "concepts": ["MD5", "SHA", "NTLM", "bcrypt"],
        "tools": ["hash-identifier", "hashid", "haiti"]
    },
    74: {
        "objectives": ["Configurar John", "Aplicar reglas", "Optimizar cracking"],
        "concepts": ["Wordlist mode", "Rules", "Incremental"],
        "tools": ["john", "jumbo patch"]
    },
    75: {
        "objectives": ["Usar la GPU", "Crear masks", "Atacar hashes complejos"],
        "concepts": ["GPU acceleration", "Masks", "Rules"],
        "tools": ["hashcat", "oclhashcat"]
    },
    76: {
        "objectives": ["Entender rainbow tables", "Crear tablas personalizadas", "Conocer limitaciones"],
        "concepts": ["Reduction functions", "Chain length", "Salt vs tables"],
        "tools": ["rtgen", "ophcrack"]
    },
    77: {
        "objectives": ["Ocultar datos en imágenes", "Detectar esteganografía", "Extraer información"],
        "concepts": ["LSB", "Carriers", "Payload"],
        "tools": ["steghide", "binwalk", "strings"]
    },
    78: {
        "objectives": ["Entender PKI", "Generar claves RSA", "Firmar y verificar"],
        "concepts": ["Pública/Privada", "Primos", "Exponentes"],
        "tools": ["openssl", "gpg"]
    },
    79: {
        "objectives": ["Entender certificados", "Verificar cadenas de confianza", "Detectar problemas SSL"],
        "concepts": ["CA", "Chain of trust", "Revocation"],
        "tools": ["testssl.sh", "sslscan", "sslyze"]
    },
    80: {
        "objectives": ["Romper contraseñas de archivos", "Usar herramientas especializadas", "Optimizar ataques"],
        "concepts": ["ZIP encryption", "PDF protection"],
        "tools": ["john", "pdfcrack", "fcrackzip"]
    },
    # NIVEL 9: POST-EXPLOTACIÓN LETAL
    81: {
        "objectives": ["Encontrar vectores de escalada", "Explotar misconfiguraciones", "Obtener root"],
        "concepts": ["SUID", "Capabilities", "Cron jobs"],
        "tools": ["linpeas", "LinEnum", "linux-exploit-suggester"]
    },
    82: {
        "objectives": ["Escalar en Windows", "Explotar servicios", "Usar técnicas modernas"],
        "concepts": ["Services", "Tokens", "UAC bypass"],
        "tools": ["winpeas", "PowerUp", "BeRoot"]
    },
    83: {
        "objectives": ["Extraer hashes de memoria", "Obtener credenciales plaintext", "Usar técnicas avanzadas"],
        "concepts": ["LSASS", "SAM", "DPAPI"],
        "tools": ["mimikatz", "pypykatz", "secretsdump"]
    },
    84: {
        "objectives": ["Instalar keyloggers", "Capturar credenciales", "Exfiltrar datos"],
        "concepts": ["Hook", "API interception", "Covert channels"],
        "tools": ["keyscan", "logkeys", "pynput"]
    },
    85: {
        "objectives": ["Moverse en la red", "Usar credenciales robadas", "Acceder a otros sistemas"],
        "concepts": ["Pass the Hash", "Pass the Ticket", "SMB relay"],
        "tools": ["psexec", "wmiexec", "evil-winrm"]
    },
    86: {
        "objectives": ["Extraer datos sin detección", "Usar canales ocultos", "Evadir DLP"],
        "concepts": ["Covert channels", "Encoding", "Fragmentation"],
        "tools": ["DNS exfil", "ICMP tunneling", "steganography"]
    },
    87: {
        "objectives": ["Mantener acceso permanente", "Sobrevivir parches", "Evadir detección"],
        "concepts": ["Persistence mechanisms", "Registry", "Scheduled tasks"],
        "tools": ["meterpreter persistence", "golden ticket"]
    },
    88: {
        "objectives": ["Eliminar rastros", "Modificar logs", "Evadir análisis forense"],
        "concepts": ["Log tampering", "Timestamps", "File wiping"],
        "tools": ["timestomp", "log cleaner", "shred"]
    },
    89: {
        "objectives": ["Entender rootkits", "Detectar rootkits", "Conocer técnicas modernas"],
        "concepts": ["Kernel mode", "User mode", "Hooking"],
        "tools": ["rkhunter", "chkrootkit"]
    },
    90: {
        "objectives": ["Entender Kerberos", "Crear Golden Tickets", "Mantener acceso AD permanente"],
        "concepts": ["KRBTGT", "TGT", "Domain persistence"],
        "tools": ["mimikatz", "impacket"]
    },
    # NIVEL 10: DIOS DEL ROOT
    91: {
        "objectives": ["Capturar handshakes", "Crackear WPA2", "Usar ataques avanzados"],
        "concepts": ["Four-way handshake", "PMKID", "Evil twin"],
        "tools": ["aircrack-ng", "airgeddon", "fluxion"]
    },
    92: {
        "objectives": ["Interceptar tráfico", "Realizar ARP spoofing", "Modificar paquetes en vuelo"],
        "concepts": ["ARP cache", "SSL stripping", "DNS spoofing"],
        "tools": ["ettercap", "bettercap", "mitmproxy"]
    },
    93: {
        "objectives": ["Dominar OWASP Top 10", "Realizar pentesting web completo", "Crear reportes profesionales"],
        "concepts": ["Injection", "Broken Auth", "XSS", "SSRF"],
        "tools": ["burpsuite", "OWASP ZAP"]
    },
    94: {
        "objectives": ["Dominar Burp Suite", "Usar extensiones", "Automatizar testing"],
        "concepts": ["Proxy", "Intruder", "Repeater", "Extender"],
        "tools": ["Burp Suite Pro"]
    },
    95: {
        "objectives": ["Analizar apps móviles", "Hacer reversing de APK", "Interceptar tráfico móvil"],
        "concepts": ["APK analysis", "Root detection bypass", "SSL pinning"],
        "tools": ["jadx", "frida", "objection"]
    },
    96: {
        "objectives": ["Desensamblar binarios", "Analizar malware", "Entender código compilado"],
        "concepts": ["Disassembly", "Debugging", "Patching"],
        "tools": ["Ghidra", "IDA", "radare2"]
    },
    97: {
        "objectives": ["Desarrollar exploits propios", "Bypassear protecciones", "Crear shellcode custom"],
        "concepts": ["ASLR", "DEP", "Stack Canaries"],
        "tools": ["pwntools", "ROPgadget", "gdb-peda"]
    },
    98: {
        "objectives": ["Auditar clouds", "Explotar misconfigs", "Entender cloud security"],
        "concepts": ["S3 buckets", "IAM", "Metadata service"],
        "tools": ["ScoutSuite", "Pacu", "prowler"]
    },
    99: {
        "objectives": ["Entender metodologías", "Simular adversarios", "Defender infraestructuras"],
        "concepts": ["MITRE ATT&CK", "Kill Chain", "Purple Team"],
        "tools": ["Atomic Red Team", "Caldera"]
    },
    100: {
        "objectives": ["Desarrollar carrera profesional", "Obtener certificaciones", "Liderar equipos de seguridad"],
        "concepts": ["Governance", "Risk Management", "Compliance"],
        "tools": ["Frameworks", "Policies", "Leadership"]
    }
}

def get_module_content(module_id: int) -> dict:
    """Returns the extended content for a module or a default if not found."""
    return MODULE_CONTENT.get(module_id, {
        "objectives": ["Completar este módulo", "Aplicar conocimientos", "Avanzar al siguiente nivel"],
        "concepts": ["Seguridad", "Hacking Ético", "Pentesting"],
        "tools": ["Kali Linux", "Terminal"]
    })

def generate_module_html(module_id: int) -> str:
    """Generates HTML content for the objectives and concepts section."""
    content = get_module_content(module_id)
    
    objectives_html = "".join([f"<li>{obj}</li>" for obj in content.get("objectives", [])])
    concepts_html = "".join([f"<span class='concept-tag'>{c}</span>" for c in content.get("concepts", [])])
    tools_html = "".join([f"<span class='tool-tag'>{t}</span>" for t in content.get("tools", [])])
    
    return f"""
    <div class="content-section">
        <h2 class="section-title">🎯 Objetivos de Aprendizaje</h2>
        <ul class="objectives-list">
            {objectives_html}
        </ul>
    </div>
    
    <div class="content-section">
        <h2 class="section-title">📚 Conceptos Clave</h2>
        <div class="tags-container">
            {concepts_html}
        </div>
    </div>
    
    <div class="content-section">
        <h2 class="section-title">🛠️ Herramientas</h2>
        <div class="tags-container">
            {tools_html}
        </div>
    </div>
    """
