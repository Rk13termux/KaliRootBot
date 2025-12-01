import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

# Configuración
ASSETS_DIR = "/home/sebas/RK13/botkaliroot/KaliRootBot/assets"
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

def create_hacker_image(filename, text, color=(0, 255, 0)):
    # Crear fondo negro
    width, height = 800, 400
    img = Image.new('RGB', (width, height), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    
    # Efecto Matrix (Líneas aleatorias)
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        w = random.randint(10, 100)
        draw.line([(x, y), (x + w, y)], fill=(0, 50, 0), width=1)

    # Dibujar Borde
    draw.rectangle([(10, 10), (width-10, height-10)], outline=color, width=3)
    
    # Intentar cargar fuente, sino usar default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        subfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
        subfont = ImageFont.load_default()

    # Texto Central
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    # Sombra del texto
    draw.text((x+2, y+2), text, font=font, fill=(0, 100, 0))
    # Texto principal
    draw.text((x, y), text, font=font, fill=color)
    
    # Subtítulo
    sub = "KALI ROOT BOT SYSTEM"
    sub_bbox = draw.textbbox((0, 0), sub, font=subfont)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(((width - sub_w)/2, height - 40), sub, font=subfont, fill=(100, 100, 100))

    # Guardar
    path = os.path.join(ASSETS_DIR, filename)
    img.save(path)
    print(f"Generada: {path}")

# Generar Assets
create_hacker_image("welcome.jpg", "BIENVENIDO HACKER", color=(0, 255, 0))     # Verde Matrix
create_hacker_image("learning.jpg", "RUTA DE APRENDIZAJE", color=(0, 200, 255)) # Azul Cyan
create_hacker_image("labs.jpg", "LABORATORIOS DE ÉLITE", color=(255, 50, 50))   # Rojo Alerta

print("¡Assets generados correctamente!")
