import time
import json
from telegraph_manager import TelegraphManager
# Importamos los módulos actuales para leer títulos y descripciones
# Hack para importar desde el directorio actual sin problemas de paquete
import sys
import os
sys.path.append(os.getcwd())
from learning_content import MODULES

def generate_html_content(title, desc, mod_id):
    """
    Genera contenido HTML dinámico basado en el título del módulo.
    Intenta ser inteligente con los comandos según palabras clave.
    """
    
    # Detección de palabras clave para comandos
    cmd_example = "sudo apt update && sudo apt upgrade -y"
    tool_name = "Linux"
    
    title_lower = title.lower()
    
    if "nmap" in title_lower:
        cmd_example = "nmap -sC -sV -oN scan.txt 192.168.1.1"
        tool_name = "Nmap"
    elif "metasploit" in title_lower:
        cmd_example = "msfconsole -q"
        tool_name = "Metasploit Framework"
    elif "wireshark" in title_lower:
        cmd_example = "wireshark &"
        tool_name = "Wireshark"
    elif "sql" in title_lower:
        cmd_example = "sqlmap -u 'http://target.com/page.php?id=1' --dbs"
        tool_name = "SQLMap"
    elif "burp" in title_lower:
        cmd_example = "java -jar burpsuite_pro.jar"
        tool_name = "Burp Suite"
    elif "aircrack" in title_lower:
        cmd_example = "airmon-ng start wlan0"
        tool_name = "Aircrack-ng"
    elif "hash" in title_lower:
        cmd_example = "hashcat -m 0 -a 0 hash.txt rockyou.txt"
        tool_name = "Hashcat"
    elif "python" in title_lower:
        cmd_example = "python3 exploit.py"
        tool_name = "Python"
    elif "bash" in title_lower:
        cmd_example = "./script.sh"
        tool_name = "Bash"
    elif "tor" in title_lower:
        cmd_example = "service tor start"
        tool_name = "Tor"
    elif "vpn" in title_lower:
        cmd_example = "openvpn --config config.ovpn"
        tool_name = "OpenVPN"
        
    html = f"""
    <h3>🛡️ Módulo {mod_id}: {title}</h3>
    <p><i>{desc}</i></p>
    <hr>
    <h4>🎯 Introducción</h4>
    <p>Bienvenido a este módulo fundamental sobre <b>{tool_name}</b>. En el mundo del hacking ético y la ciberseguridad, dominar esta habilidad es crucial para realizar auditorías profesionales.</p>
    
    <h4>🛠️ Conceptos Clave</h4>
    <ul>
        <li>Entendiendo la arquitectura de {tool_name}.</li>
        <li>Casos de uso en entornos reales.</li>
        <li>Mejores prácticas de seguridad y anonimato.</li>
    </ul>
    
    <h4>💻 Laboratorio Práctico</h4>
    <p>Abre tu terminal en Kali Linux y prueba el siguiente comando para verificar tu configuración:</p>
    <pre><code>{cmd_example}</code></pre>
    <p>Este comando es el punto de partida. Asegúrate de entender cada parámetro antes de ejecutarlo en un entorno de producción.</p>
    
    <h4>⚠️ Advertencia Ética</h4>
    <p>Recuerda: <b>El gran poder conlleva una gran responsabilidad</b>. Utiliza este conocimiento únicamente en sistemas propios o donde tengas autorización explícita por escrito.</p>
    
    <blockquote>"La única forma de protegerse es conociendo al enemigo."</blockquote>
    """
    return html

def main():
    tm = TelegraphManager()
    new_links = {}
    
    print(f"🚀 Iniciando generación masiva para {len(MODULES)} módulos...")
    print("Esto puede tardar unos minutos. Por favor espera.")
    
    for mod_id, data in MODULES.items():
        title = data['title']
        desc = data['desc']
        
        print(f"[{mod_id}/100] Generando: {title}...", end="", flush=True)
        
        try:
            # Generar contenido
            html_content = generate_html_content(title, desc, mod_id)
            
            # Publicar en Telegraph
            # Usamos un título corto para la página para que la URL sea limpia
            page_title = f"KaliRoot Mod {mod_id}: {title[:30]}..."
            url = tm.create_page(page_title, html_content)
            
            # Guardar URL
            new_links[mod_id] = url
            print(f" ✅ OK")
            
            # Pequeña pausa para no saturar la API (rate limiting)
            time.sleep(0.5)
            
        except Exception as e:
            print(f" ❌ ERROR: {e}")
            new_links[mod_id] = data['link'] # Mantener el viejo si falla
            
    # Guardar resultados en un JSON temporal
    with open("new_module_links.json", "w") as f:
        json.dump(new_links, f, indent=4)
        
    print("\n✨ ¡Generación Completa! Enlaces guardados en new_module_links.json")

if __name__ == "__main__":
    main()
