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
    # Always recreate to ensure new dimensions/colors apply if file exists but is old
    # Create a 1900x900 dark image with Telegram Blue border
    telegram_blue = (0, 136, 204)
    img = Image.new('RGB', (1900, 900), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    # Draw border
    draw.rectangle([20, 20, 1880, 880], outline=telegram_blue, width=10)
    # Save
    img.save(CERT_TEMPLATE_PATH)
    logger.info("Created/Updated fallback certificate template.")

def generate_certificate(user_name: str, user_id: int, module_title: str) -> str:
    """
    Generates a certificate image for the user.
    Returns the path to the generated image.
    """
    try:
        # Force recreation of template to ensure correct size/color
        create_fallback_template()
        
        img = Image.open(CERT_TEMPLATE_PATH)
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Colors
        text_color = (255, 255, 255)
        telegram_blue = (0, 136, 204) # Telegram Blue
        
        # Load fonts (Scaled up for 1900x900)
        try:
            # Try to load a ttf if available, else default
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80) # Bigger
            name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 100) # Bigger
            text_font = ImageFont.truetype("DejaVuSans.ttf", 40) # Bigger
            module_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70) # Bigger
        except OSError:
            # Fallback to default PIL font (very small, but works)
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            module_font = ImageFont.load_default()

        # Draw Content - Adjusted for 1900x900
        
        # 1. Title
        draw.text((width/2, 150), "CERTIFICADO DE FINALIZACIÓN", font=title_font, fill=telegram_blue, anchor="mm")
        
        # 2. "Awarded to"
        draw.text((width/2, 300), "Otorgado a:", font=text_font, fill=text_color, anchor="mm")
        
        # 3. User Name
        draw.text((width/2, 400), user_name.upper(), font=name_font, fill=text_color, anchor="mm")
        
        # 4. User ID
        draw.text((width/2, 480), f"ID: {user_id}", font=text_font, fill=(150, 150, 150), anchor="mm")
        
        # 5. "For completing"
        draw.text((width/2, 600), "Por completar exitosamente el módulo:", font=text_font, fill=text_color, anchor="mm")
        
        # 6. Module Title
        draw.text((width/2, 680), module_title, font=module_font, fill=telegram_blue, anchor="mm")
        
        # 7. Date
        date_str = datetime.now().strftime("%d/%m/%Y")
        draw.text((width/2, 800), f"Fecha: {date_str}", font=text_font, fill=text_color, anchor="mm")
        
        # Save output
        output_filename = f"cert_{user_id}_{datetime.now().timestamp()}.png"
        output_path = os.path.join(ASSETS_DIR, output_filename)
        img.save(output_path)
        
        return output_path
    except Exception as e:
        logger.exception(f"Error generating certificate: {e}")
        return None
