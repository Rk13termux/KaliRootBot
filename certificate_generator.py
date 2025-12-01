from PIL import Image, ImageDraw, ImageFont
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

ASSETS_DIR = "assets"
CERT_TEMPLATE_PATH = os.path.join(ASSETS_DIR, "cert_template.png")
FONT_PATH = os.path.join(ASSETS_DIR, "Roboto-Bold.ttf") # Fallback font usually needed

def ensure_assets_dir():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)

def create_fallback_template():
    """Creates a simple placeholder certificate template if none exists."""
    ensure_assets_dir()
    if not os.path.exists(CERT_TEMPLATE_PATH):
        # Create a 800x600 dark image with gold border
        img = Image.new('RGB', (800, 600), color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        # Draw border
        draw.rectangle([10, 10, 790, 590], outline=(218, 165, 32), width=5)
        # Save
        img.save(CERT_TEMPLATE_PATH)
        logger.info("Created fallback certificate template.")

def generate_certificate(user_name: str, user_id: int, module_title: str) -> str:
    """
    Generates a certificate image for the user.
    Returns the path to the generated image.
    """
    try:
        create_fallback_template()
        
        img = Image.open(CERT_TEMPLATE_PATH)
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Colors
        text_color = (255, 255, 255)
        gold_color = (218, 165, 32)
        
        # Load fonts (try to load a system font or default)
        try:
            # Try to load a ttf if available, else default
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
            name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
            text_font = ImageFont.truetype("DejaVuSans.ttf", 20)
        except OSError:
            # Fallback to default PIL font (very small, but works)
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Draw Content
        # 1. Title
        draw.text((width/2, 100), "CERTIFICADO DE FINALIZACIÓN", font=title_font, fill=gold_color, anchor="mm")
        
        # 2. "Awarded to"
        draw.text((width/2, 200), "Otorgado a:", font=text_font, fill=text_color, anchor="mm")
        
        # 3. User Name
        draw.text((width/2, 260), user_name.upper(), font=name_font, fill=text_color, anchor="mm")
        
        # 4. User ID
        draw.text((width/2, 310), f"ID: {user_id}", font=text_font, fill=(150, 150, 150), anchor="mm")
        
        # 5. "For completing"
        draw.text((width/2, 380), "Por completar exitosamente el módulo:", font=text_font, fill=text_color, anchor="mm")
        
        # 6. Module Title
        draw.text((width/2, 430), module_title, font=title_font, fill=gold_color, anchor="mm")
        
        # 7. Date
        date_str = datetime.now().strftime("%d/%m/%Y")
        draw.text((width/2, 530), f"Fecha: {date_str}", font=text_font, fill=text_color, anchor="mm")
        
        # Save output
        output_filename = f"cert_{user_id}_{datetime.now().timestamp()}.png"
        output_path = os.path.join(ASSETS_DIR, output_filename)
        img.save(output_path)
        
        return output_path
    except Exception as e:
        logger.exception(f"Error generating certificate: {e}")
        return None
