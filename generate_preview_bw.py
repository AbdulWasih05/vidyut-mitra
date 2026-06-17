import io
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1350

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_DARK = (60, 60, 60)
GRAY_MED = (120, 120, 120)
GRAY_LIGHT = (220, 220, 220)

def _get_font(size, bold=False):
    fonts = [
        "arialbd.ttf" if bold else "arial.ttf", 
        "segoeuib.ttf" if bold else "segoeui.ttf", 
        "Helvetica-Bold.ttf" if bold else "Helvetica.ttf",
        "FreeSansBold.ttf" if bold else "FreeSans.ttf"
    ]
    for f in fonts:
        try:
            return ImageFont.truetype(f, size)
        except:
            pass
    return ImageFont.load_default()

def draw_text_centered(draw, pos, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((pos[0] - w/2, pos[1]), text, fill=fill, font=font)

def generate_preview():
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # Typography
    f_title = _get_font(56, True)
    f_h1 = _get_font(100, True)
    f_h2 = _get_font(46, True)
    f_h3 = _get_font(36, True)
    f_body = _get_font(30, False)
    f_small_bold = _get_font(26, True)
    f_small = _get_font(26, False)
    f_tiny = _get_font(22, False)

    # --- Header ---
    draw.rectangle([0, 0, WIDTH, 120], fill=BLACK)
    draw.text((60, 30), "VidyutMitra", fill=WHITE, font=f_title)
    
    bbox = draw.textbbox((0,0), "MESCOM BILL REPORT", font=f_small_bold)
    draw.text((WIDTH - 60 - (bbox[2]-bbox[0]), 45), "MESCOM BILL REPORT", fill=WHITE, font=f_small_bold)

    y = 160

    # --- Main Metric ---
    draw.text((60, y), "NET BILL AMOUNT", fill=GRAY_MED, font=f_small_bold)
    y += 40
    draw.text((60, y), "Rs. 1,943", fill=BLACK, font=f_h1)
    
    y += 140
    
    # Metadata / Context split 
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 30
    draw.text((60, y), "210 UNITS CONSUMED", fill=BLACK, font=f_small_bold)
    draw.text((450, y), "3 KW SANCTIONED LOAD", fill=BLACK, font=f_small_bold)
    
    y += 60
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4) # thick separator
    y += 60

    # --- Fixed Charge Trap ---
    box1_y1 = y
    box1_y2 = y + 260
    # Heavy outline
    draw.rectangle([60, box1_y1, WIDTH - 60, box1_y2], outline=BLACK, width=6)
    
    # Alert Header
    draw.rectangle([60, box1_y1, WIDTH - 60, box1_y1 + 70], fill=BLACK)
    draw.text((90, box1_y1 + 18), "ATTENTION: SANCTIONED LOAD OVER-PROVISIONED", fill=WHITE, font=f_small_bold)
    
    # Alert Body
    draw.text((90, box1_y1 + 100), "Your 3 kW load is higher than your estimated 1.5 kW peak usage.", fill=GRAY_DARK, font=f_body)
    draw.text((90, box1_y1 + 155), "Recommended Action:", fill=GRAY_MED, font=f_small)
    draw.text((90, box1_y1 + 195), "Reduce to 2 kW to save Rs. 145 / mo (Rs. 1,740 / year)", fill=BLACK, font=f_h3)
    
    y = box1_y2 + 80

    # --- Solar ROI ---
    draw.text((60, y), "ROOFTOP SOLAR ROI", fill=BLACK, font=f_h2)
    y += 70
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 40

    # Grid config
    col1 = 60
    col2 = WIDTH // 2 + 20
    
    # Row 1
    draw.text((col1, y), "RECOMMENDED SYSTEM", fill=GRAY_MED, font=f_small_bold)
    draw.text((col1, y + 40), "3 kW", fill=BLACK, font=f_h3)
    
    draw.text((col2, y), "NET COST (POST SUBSIDY)", fill=GRAY_MED, font=f_small_bold)
    draw.text((col2, y + 40), "Rs. 87,000", fill=BLACK, font=f_h3)
    
    y += 120
    
    # Row 2
    draw.text((col1, y), "ESTIMATED PAYBACK", fill=GRAY_MED, font=f_small_bold)
    draw.text((col1, y + 40), "3.8 Years", fill=BLACK, font=f_h3)
    
    draw.text((col2, y), "LIFETIME SAVINGS (25 YRS)", fill=GRAY_MED, font=f_small_bold)
    draw.text((col2, y + 40), "~Rs. 3.2 Lakh", fill=BLACK, font=f_h3)

    y += 120

    # Row 3
    draw.text((col1, y), "CO2 AVOIDED", fill=GRAY_MED, font=f_small_bold)
    draw.text((col1, y + 40), "2.98 tonnes / year", fill=BLACK, font=f_h3)

    y += 120
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4) # thick bottom separator

    # --- Footer ---
    y = HEIGHT - 80
    draw.text((60, y), "DATA SOURCE: KERC TARIFF ORDER 2025 | CEA DATABASE V21.0 | PM SURYA GHAR", fill=GRAY_MED, font=f_tiny)

    img.save("preview_bw_design.png")
    print("Preview generated as preview_bw_design.png")

if __name__ == "__main__":
    generate_preview()