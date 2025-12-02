import json
import re

# 1. Leer los nuevos enlaces
with open("new_module_links.json", "r") as f:
    links = json.load(f)

# Convertir claves a int
links = {int(k): v for k, v in links.items()}

# 2. Leer el archivo original
with open("learning_content.py", "r") as f:
    content = f.read()

# 3. Preparar el diccionario como string
links_str = "MODULE_LINKS = {\n"
for k, v in sorted(links.items()):
    links_str += f"    {k}: \"{v}\",\n"
links_str += "}\n"

# 4. Modificar el contenido
# Insertamos MODULE_LINKS antes de la función add_mod
if "MODULE_LINKS = {" not in content:
    content = content.replace("MODULES = {}", f"MODULES = {{}}\n\n{links_str}")
else:
    # Si ya existe (por si corremos esto 2 veces), lo reemplazamos con regex
    content = re.sub(r"MODULE_LINKS = \{.*?\}", links_str, content, flags=re.DOTALL)

# Modificamos add_mod para usar MODULE_LINKS
# Buscamos la función y cambiamos la línea de asignación
old_func = """def add_mod(id, sec, title, desc):
    # Use local asset path
    img_path = f"assets/module_{id}.jpg"
    MODULES[id] = {"section": sec, "title": title, "desc": desc, "img": img_path, "link": DEFAULT_LINK}"""

new_func = """def add_mod(id, sec, title, desc):
    # Use local asset path
    img_path = f"assets/module_{id}.jpg"
    # Use specific link if available, else default
    link = MODULE_LINKS.get(id, DEFAULT_LINK)
    MODULES[id] = {"section": sec, "title": title, "desc": desc, "img": img_path, "link": link}"""

if old_func in content:
    content = content.replace(old_func, new_func)
else:
    # Si no coincide exactamente por espacios, usamos un reemplazo más agresivo pero seguro
    # Reemplazamos la línea específica dentro de add_mod
    content = re.sub(
        r'MODULES\[id\] = \{.*?"link": DEFAULT_LINK\}', 
        'link = MODULE_LINKS.get(id, DEFAULT_LINK)\n    MODULES[id] = {"section": sec, "title": title, "desc": desc, "img": img_path, "link": link}', 
        content
    )

# 5. Guardar
with open("learning_content.py", "w") as f:
    f.write(content)

print("✅ learning_content.py actualizado con los nuevos enlaces.")
