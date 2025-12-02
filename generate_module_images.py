import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

# Asegurar directorio assets
ASSETS_DIR = "assets"
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

def create_hacker_bg(width, height):
    # Fondo negro
    img = Image.new('RGB', (width, height), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    
    # Efecto Matrix simple (líneas verticales verdes tenues)
    for _ in range(50):
        x = random.randint(0, width)
        y_start = random.randint(0, height)
        length = random.randint(50, 200)
        opacity = random.randint(20, 100)
        draw.line([(x, y_start), (x, y_start + length)], fill=(0, 255, 0, opacity), width=1)
        
    return img

def generate_module_image(module_id, title):
    width, height = 800, 400
    img = create_hacker_bg(width, height)
    draw = ImageDraw.Draw(img)
    
    # Intentar cargar una fuente, si no usar default
    try:
        # Usar una fuente monoespaciada si existe en el sistema, sino default
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Texto Central: MÓDULO X
    text_main = f"MÓDULO {module_id}"
    
    # Centrar texto
    bbox = draw.textbbox((0, 0), text_main, font=font_large)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) / 2
    y = (height - text_h) / 2 - 40
    
    # Sombra neón
    draw.text((x+2, y+2), text_main, font=font_large, fill=(0, 50, 0))
    draw.text((x, y), text_main, font=font_large, fill=(0, 255, 0))
    
    # Título del módulo (truncado si es muy largo)
    if len(title) > 40:
        title = title[:37] + "..."
        
    bbox_t = draw.textbbox((0, 0), title, font=font_small)
    text_wt = bbox_t[2] - bbox_t[0]
    
    xt = (width - text_wt) / 2
    yt = y + text_h + 20
    
    draw.text((xt, yt), title, font=font_small, fill=(200, 255, 200))
    
    # Borde
    draw.rectangle([(0,0), (width-1, height-1)], outline=(0, 255, 0), width=5)
    
    # Guardar
    filename = os.path.join(ASSETS_DIR, f"module_{module_id}.jpg")
    img.save(filename, quality=85)
    print(f"Generada: {filename}")

# Definición de módulos (copiada simplificada para obtener títulos)
# En un caso real importaría MODULES, pero para evitar dependencias circulares o problemas de import,
# voy a leer el archivo o simplemente generar genéricos si no puedo importar.
# Mejor importo MODULES de learning_content si es posible.

import sys
sys.path.append('.')
try:
    from learning_content import MODULES
    print(f"Importados {len(MODULES)} módulos.")
    for mod_id, data in MODULES.items():
        generate_module_image(mod_id, data['title'])
except Exception as e:
    print(f"Error importando módulos: {e}. Generando genéricos.")
    for i in range(1, 101):
        generate_module_image(i, "Kali Linux Training")

print("¡Generación completa!")
