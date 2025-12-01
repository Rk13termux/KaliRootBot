"""
Contenido Masivo de Laboratorios Prácticos (100 Escenarios).
"""

LAB_CATEGORIES = {
    "linux": "🐧 Linux & Bash (Fundamentos)",
    "network": "🌐 Hacking de Redes",
    "web": "🌍 Hacking Web (OWASP)",
    "crypto": "🔐 Criptografía & Esteganografía",
    "forensics": "🕵️‍♂️ Forense Digital",
    "osint": "👁️ OSINT & Reconocimiento",
    "privesc": "👑 Escalada de Privilegios",
    "wifi": "📡 Hacking Wi-Fi & Radio",
    "mobile": "📱 Hacking Móvil (Android/iOS)",
    "malware": "🦠 Malware & Ingeniería Inversa"
}

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

# ==========================================
# 1. 🐧 LINUX & BASH (1-10)
# ==========================================
add_lab(1, "linux", "Identidad", "Descubre quién eres en el sistema.", "whoami", "root", "Usuario actual:", "root", 50, False)
add_lab(2, "linux", "Archivos Ocultos", "Encuentra el config secreto.", "ls -la", ".secret", "Nombre del archivo oculto:", ".secret", 50, False)
add_lab(3, "linux", "Lectura de Archivos", "Lee la contraseña.", "cat pass.txt", "123456", "Contenido:", "123456", 50, False)
add_lab(4, "linux", "Permisos", "Verifica permisos de ejecución.", "ls -l script.sh", "-rwxr-xr-x 1 root root", "¿Tiene permiso de ejecución el dueño? (Si/No)", "Si", 100, True)
add_lab(5, "linux", "Procesos", "Encuentra el PID de apache.", "ps aux | grep apache", "root 1337 0.0 0.1 apache2", "PID del proceso:", "1337", 100, True)
add_lab(6, "linux", "Redirecciones", "Guarda 'hola' en test.txt.", "echo 'hola' > test.txt", "", "Comando para añadir sin sobrescribir (usando >>):", ">>", 100, True)
add_lab(7, "linux", "Búsqueda", "Busca archivos .conf en /etc.", "find /etc -name '*.conf'", "/etc/apache2.conf", "Ruta encontrada:", "/etc/apache2.conf", 100, True)
add_lab(8, "linux", "Networking Local", "Ver tu IP.", "ip a", "inet 192.168.1.50/24", "Tu dirección IP:", "192.168.1.50", 100, True)
add_lab(9, "linux", "Historial", "Ver comandos anteriores.", "history", "1 ping google.com\n2 cat /etc/shadow", "Comando peligroso ejecutado:", "cat /etc/shadow", 100, True)
add_lab(10, "linux", "Variables", "Ver el PATH.", "echo $PATH", "/usr/bin:/bin", "Separador de directorios:", ":", 100, True)

# ==========================================
# 2. 🌐 HACKING DE REDES (11-20)
# ==========================================
add_lab(11, "network", "Ping Sweep", "Detecta hosts vivos.", "nmap -sn 192.168.1.0/24", "Host is up (192.168.1.10)", "IP activa encontrada:", "192.168.1.10", 100, True)
add_lab(12, "network", "Escaneo TCP", "Puertos abiertos.", "nmap -sS target", "22/tcp open ssh", "Puerto SSH:", "22", 100, True)
add_lab(13, "network", "Versiones", "Versión de servicio.", "nmap -sV target", "80/tcp open http Apache 2.4.49", "Versión de Apache:", "2.4.49", 100, True)
add_lab(14, "network", "OS Detection", "Sistema Operativo.", "nmap -O target", "OS details: Linux 4.15 - 5.6", "Familia de OS:", "Linux", 100, True)
add_lab(15, "network", "Scripts NSE", "Vuln scan.", "nmap --script vuln target", "VULNERABLE: SSL POODLE", "Vulnerabilidad detectada:", "POODLE", 150, True)
add_lab(16, "network", "Netcat Listener", "Escuchar puerto.", "nc -lvp 4444", "listening on [any] 4444 ...", "Puerto en escucha:", "4444", 100, True)
add_lab(17, "network", "Netcat Connect", "Conectar a puerto.", "nc target 80", "GET / HTTP/1.1", "Método HTTP usado:", "GET", 100, True)
add_lab(18, "network", "Wireshark Filtros", "Filtrar HTTP.", "http.request.method == POST", "POST /login.php", "Archivo solicitado:", "/login.php", 150, True)
add_lab(19, "network", "ARP Spoofing", "Ver tabla ARP.", "arp -a", "192.168.1.1 at 00:11:22:33:44:55", "MAC del Gateway:", "00:11:22:33:44:55", 150, True)
add_lab(20, "network", "Hydra SSH", "Bruteforce SSH.", "hydra -l root -P pass.txt ssh://target", "login: root password: toor", "Contraseña encontrada:", "toor", 200, True)

# ==========================================
# 3. 🌍 HACKING WEB (21-30)
# ==========================================
add_lab(21, "web", "Robots.txt", "Archivos ocultos.", "curl target.com/robots.txt", "Disallow: /admin_panel", "Ruta prohibida:", "/admin_panel", 100, True)
add_lab(22, "web", "Gobuster Dir", "Fuzzing directorios.", "gobuster dir -u target.com -w list.txt", "/uploads (Status: 200)", "Directorio encontrado:", "/uploads", 100, True)
add_lab(23, "web", "SQLi Error", "Provocar error.", "id=1'", "You have an error in your SQL syntax", "Vulnerable a SQLi? (Si/No):", "Si", 100, True)
add_lab(24, "web", "SQLMap DBS", "Listar bases de datos.", "sqlmap -u target --dbs", "[*] users_db", "Nombre BD:", "users_db", 150, True)
add_lab(25, "web", "XSS Reflejado", "Payload alert.", "<script>alert(1)</script>", "Popup: 1", "Función JS ejecutada:", "alert", 100, True)
add_lab(26, "web", "LFI Básico", "Leer passwd.", "page=../../../../etc/passwd", "root:x:0:0:root", "Usuario root encontrado? (Si/No):", "Si", 150, True)
add_lab(27, "web", "Command Injection", "Ejecutar comando.", "ip=127.0.0.1; whoami", "www-data", "Usuario web:", "www-data", 150, True)
add_lab(28, "web", "Cookie Tampering", "Modificar cookie.", "Cookie: role=admin", "Welcome Admin!", "Rol necesario:", "admin", 150, True)
add_lab(29, "web", "HTML Comments", "Ver código fuente.", "view-source", "<!-- TODO: Remove debug user 'test' -->", "Usuario debug:", "test", 100, True)
add_lab(30, "web", "WPScan", "Escanear WordPress.", "wpscan --url target.com", "[!] Title: WordPress 5.0", "CMS detectado:", "WordPress", 150, True)

# ==========================================
# 4. 🔐 CRIPTOGRAFÍA (31-40)
# ==========================================
add_lab(31, "crypto", "Base64 Decode", "Decodificar.", "echo 'SGFja2Vy' | base64 -d", "Hacker", "Texto plano:", "Hacker", 100, True)
add_lab(32, "crypto", "ROT13", "Cifrado César.", "rot13 'Ubyb'", "Hola", "Texto plano:", "Hola", 100, True)
add_lab(33, "crypto", "Hash ID", "Identificar hash.", "hash-identifier '21232f297a57a5a743894a0e4a801fc3'", "MD5", "Algoritmo:", "MD5", 100, True)
add_lab(34, "crypto", "Crack MD5", "Romper hash.", "hashcat -m 0 hash.txt wordlist.txt", "admin123", "Password:", "admin123", 150, True)
add_lab(35, "crypto", "SSH Keys", "Permisos llave privada.", "chmod 600 id_rsa", "", "Permiso octal seguro:", "600", 100, True)
add_lab(36, "crypto", "Steghide Extract", "Esteganografía.", "steghide extract -sf image.jpg", "secret.txt extracted", "Archivo extraído:", "secret.txt", 150, True)
add_lab(37, "crypto", "Exif Data", "Metadatos.", "exiftool photo.jpg", "GPS: 40.7128, -74.0060", "Dato encontrado:", "GPS", 100, True)
add_lab(38, "crypto", "GPG Decrypt", "Descifrar archivo.", "gpg -d msg.gpg", "Top Secret", "Mensaje:", "Top Secret", 150, True)
add_lab(39, "crypto", "Zip Crack", "Fuerza bruta zip.", "fcrackzip -u -D -p rockyou.txt file.zip", "PASSWORD FOUND!!!!: qwerty", "Password zip:", "qwerty", 150, True)
add_lab(40, "crypto", "Hex to ASCII", "Conversión.", "xxd -r -p", "Kali", "Texto:", "Kali", 100, True)

# ==========================================
# 5. 🕵️‍♂️ FORENSE DIGITAL (41-50)
# ==========================================
add_lab(41, "forensics", "File Signature", "Verificar tipo archivo.", "file evidence", "JPEG image data", "Tipo de archivo:", "JPEG", 100, True)
add_lab(42, "forensics", "Strings", "Cadenas legibles.", "strings mem.dump | grep pass", "pass=SuperSecret", "Contraseña en memoria:", "SuperSecret", 150, True)
add_lab(43, "forensics", "Binwalk", "Analizar firmware.", "binwalk firmware.bin", "Squashfs filesystem", "Sistema de archivos:", "Squashfs", 150, True)
add_lab(44, "forensics", "Deleted Files", "Recuperar archivos.", "foremost -i disk.img", "Output: jpg, pdf", "Herramienta usada:", "foremost", 150, True)
add_lab(45, "forensics", "Browser History", "SQLite DB.", "sqlite3 history.db 'select url from urls'", "google.com", "Sitio visitado:", "google.com", 150, True)
add_lab(46, "forensics", "Network PCAP", "Analizar tráfico.", "tcpdump -r capture.pcap", "IP 10.0.0.5 > 10.0.0.1", "IP origen:", "10.0.0.5", 150, True)
add_lab(47, "forensics", "Log Analysis", "Auth logs.", "grep 'Failed password' /var/log/auth.log", "Failed password for root", "Usuario atacado:", "root", 100, True)
add_lab(48, "forensics", "Hash Check", "Integridad.", "sha256sum evidence.dd", "a1b2c3d4...", "Algoritmo usado:", "sha256", 100, True)
add_lab(49, "forensics", "Volatility", "Perfil memoria.", "volatility -f mem.vmem imageinfo", "Win7SP1x64", "Perfil sugerido:", "Win7SP1x64", 200, True)
add_lab(50, "forensics", "PDF Analysis", "Malicious PDF.", "pdfid file.pdf", "/JS 1", "Elemento sospechoso:", "/JS", 150, True)

# ==========================================
# 6. 👁️ OSINT (51-60)
# ==========================================
add_lab(51, "osint", "Whois", "Info dominio.", "whois google.com", "Registrar: MarkMonitor", "Registrador:", "MarkMonitor", 100, True)
add_lab(52, "osint", "DNS Lookup", "Registros A.", "nslookup target.com", "Address: 1.2.3.4", "Tipo de registro:", "A", 100, True)
add_lab(53, "osint", "Reverse DNS", "IP a Dominio.", "host 8.8.8.8", "dns.google", "Dominio:", "dns.google", 100, True)
add_lab(54, "osint", "Email Harvesting", "TheHarvester.", "theHarvester -d target.com -b google", "admin@target.com", "Email encontrado:", "admin@target.com", 150, True)
add_lab(55, "osint", "Google Dorks", "Búsqueda avanzada.", "site:target.com filetype:pdf", "confidential.pdf", "Operador para tipo de archivo:", "filetype", 100, True)
add_lab(56, "osint", "Shodan", "Buscador IoT.", "shodan host 1.1.1.1", "Cloudflare DNS", "Servicio:", "DNS", 150, True)
add_lab(57, "osint", "Username Check", "Sherlock.", "sherlock user123", "[+] Instagram: https://instagram.com/user123", "Red social encontrada:", "Instagram", 150, True)
add_lab(58, "osint", "Metadata PDF", "Autor documento.", "exiftool doc.pdf", "Author: Alice", "Autor:", "Alice", 100, True)
add_lab(59, "osint", "Subdomain Enum", "Sublist3r.", "sublist3r -d target.com", "dev.target.com", "Subdominio:", "dev.target.com", 150, True)
add_lab(60, "osint", "Wayback Machine", "Archivos antiguos.", "curl archive.org/...", "old-page.html", "Herramienta de archivo:", "Wayback Machine", 150, True)

# ==========================================
# 7. 👑 ESCALADA DE PRIVILEGIOS (61-70)
# ==========================================
add_lab(61, "privesc", "Sudo -l", "Listar permisos.", "sudo -l", "(root) NOPASSWD: /usr/bin/vim", "Binario permitido:", "vim", 150, True)
add_lab(62, "privesc", "SUID Files", "Bits SUID.", "find / -perm -4000", "/usr/bin/nmap", "Binario SUID:", "nmap", 150, True)
add_lab(63, "privesc", "Cron Jobs", "Tareas programadas.", "cat /etc/crontab", "root /root/backup.sh", "Script ejecutado por root:", "backup.sh", 150, True)
add_lab(64, "privesc", "Kernel Version", "Info kernel.", "uname -a", "Linux 2.6.24", "Versión Kernel:", "2.6.24", 100, True)
add_lab(65, "privesc", "Shadow File", "Permisos shadow.", "ls -l /etc/shadow", "-rw-rw-rw-", "Es escribible? (Si/No):", "Si", 150, True)
add_lab(66, "privesc", "SSH Key Root", "Llave en /tmp.", "ls /tmp", "id_rsa", "Archivo encontrado:", "id_rsa", 150, True)
add_lab(67, "privesc", "History Root", "Bash history.", "cat /root/.bash_history", "mysql -u root -p123", "Password root:", "123", 150, True)
add_lab(68, "privesc", "Writables", "Directorios escribibles.", "find / -writable -type d", "/tmp", "Directorio común:", "/tmp", 100, True)
add_lab(69, "privesc", "GTFOBins", "Exploit binario.", "less /etc/profile !/bin/sh", "#", "Shell obtenida:", "#", 200, True)
add_lab(70, "privesc", "Capabilities", "Getcap.", "getcap -r /", "/usr/bin/python = cap_setuid+ep", "Capability:", "cap_setuid", 200, True)

# ==========================================
# 8. 📡 HACKING WI-FI (71-80)
# ==========================================
add_lab(71, "wifi", "Iwconfig", "Interfaces.", "iwconfig", "wlan0: IEEE 802.11", "Interfaz wireless:", "wlan0", 100, True)
add_lab(72, "wifi", "Monitor Mode", "Activar monitor.", "airmon-ng start wlan0", "monitor mode enabled on wlan0mon", "Nueva interfaz:", "wlan0mon", 150, True)
add_lab(73, "wifi", "Airodump Scan", "Escanear redes.", "airodump-ng wlan0mon", "ESSID: Home_WiFi", "Nombre de red:", "Home_WiFi", 150, True)
add_lab(74, "wifi", "Deauth Attack", "Desconectar cliente.", "aireplay-ng --deauth 10", "Sending DeAuth", "Ataque usado:", "Deauth", 150, True)
add_lab(75, "wifi", "Handshake Capture", "WPA Handshake.", "WPA handshake: AA:BB:CC...", "Handshake captured", "Qué se capturó:", "Handshake", 200, True)
add_lab(76, "wifi", "Crack WPA", "Aircrack.", "aircrack-ng -w wordlist.txt cap.cap", "KEY FOUND! [ 12345678 ]", "Clave WiFi:", "12345678", 200, True)
add_lab(77, "wifi", "WPS Scan", "Wash.", "wash -i wlan0mon", "WPS Locked: No", "Protocolo vulnerable:", "WPS", 150, True)
add_lab(78, "wifi", "Reaver", "WPS Bruteforce.", "reaver -i wlan0mon -b BSSID", "WPS PIN: 12345670", "Dato obtenido:", "PIN", 200, True)
add_lab(79, "wifi", "Mac Changer", "Cambiar MAC.", "macchanger -r wlan0", "New MAC: 00:11:22...", "Opción para random:", "-r", 100, True)
add_lab(80, "wifi", "Evil Twin", "Concepto.", "Airbase-ng", "Fake AP created", "Nombre del ataque:", "Evil Twin", 150, True)

# ==========================================
# 9. 📱 HACKING MÓVIL (81-90)
# ==========================================
add_lab(81, "mobile", "ADB Devices", "Listar dispositivos.", "adb devices", "List of devices attached", "Comando base:", "adb", 100, True)
add_lab(82, "mobile", "ADB Shell", "Shell en Android.", "adb shell", "shell@android:/ $", "Prompt obtenido:", "$", 150, True)
add_lab(83, "mobile", "APK Tool", "Decompilar APK.", "apktool d app.apk", "Decoding AndroidManifest.xml", "Archivo manifiesto:", "AndroidManifest.xml", 150, True)
add_lab(84, "mobile", "Logcat", "Logs del sistema.", "adb logcat", "D/ActivityManager", "Comando logs:", "logcat", 100, True)
add_lab(85, "mobile", "Pull File", "Extraer archivo.", "adb pull /sdcard/pic.jpg", "1 file pulled", "Comando extraer:", "pull", 100, True)
add_lab(86, "mobile", "Screen Record", "Grabar pantalla.", "adb shell screenrecord", "/sdcard/demo.mp4", "Extensión video:", "mp4", 100, True)
add_lab(87, "mobile", "Install APK", "Instalar app.", "adb install virus.apk", "Success", "Mensaje éxito:", "Success", 150, True)
add_lab(88, "mobile", "Root Check", "Verificar root.", "adb shell su", "#", "Prompt root:", "#", 150, True)
add_lab(89, "mobile", "Metasploit Android", "Payload.", "msfvenom -p android/meterpreter...", "apk generated", "Plataforma:", "android", 200, True)
add_lab(90, "mobile", "Drozer", "Security framework.", "drozer console connect", "dz>", "Prompt drozer:", "dz>", 200, True)

# ==========================================
# 10. 🦠 MALWARE & REVERSE (91-100)
# ==========================================
add_lab(91, "malware", "File Type", "PE32 executable.", "file malware.exe", "PE32 executable (GUI) Intel 80386", "Arquitectura:", "Intel 80386", 150, True)
add_lab(92, "malware", "Strings Maliciosos", "URLs.", "strings malware.exe | grep http", "http://c2.server.com", "Dominio C2:", "c2.server.com", 150, True)
add_lab(93, "malware", "Hash Calc", "MD5.", "md5sum malware.exe", "e10adc3949ba59abbe56e057f20f883e", "Primeros 3 chars:", "e10", 100, True)
add_lab(94, "malware", "VirusTotal", "API Check.", "vt scan file.exe", "50/70 detected", "Plataforma análisis:", "VirusTotal", 150, True)
add_lab(95, "malware", "UPX Pack", "Empaquetar.", "upx -9 malware.exe", "Packed 1 file", "Herramienta packing:", "upx", 150, True)
add_lab(96, "malware", "Objdump", "Disassemble.", "objdump -d malware.o", "mov eax, 0x1", "Instrucción mover:", "mov", 200, True)
add_lab(97, "malware", "GDB Start", "Debugger.", "gdb ./program", "(gdb)", "Prompt debugger:", "(gdb)", 150, True)
add_lab(98, "malware", "Ltrace", "Librerías.", "ltrace ./program", "strcmp('pass', 'input')", "Función comparar:", "strcmp", 200, True)
add_lab(99, "malware", "Strace", "Syscalls.", "strace ./program", "open('/etc/passwd')", "Syscall abrir:", "open", 200, True)
add_lab(100, "malware", "Radare2", "Framework.", "r2 malware.exe", "[0x00400000]>", "Comando r2:", "r2", 200, True)
