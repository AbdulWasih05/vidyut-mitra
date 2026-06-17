import io
from pathlib import Path
from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import AnalysisResult, FCTReport
from backend.analysis.solar_roi import SolarROI
from backend.analysis.tariff_engine import BillComputation
from PIL import Image, ImageDraw, ImageFont

# Dimensions
WIDTH = 1080
HEIGHT = 1350

# Colors
BG_COLOR = (249, 250, 251) # Gray 50
TEXT_MAIN = (17, 24, 39) # Gray 900
TEXT_SECONDARY = (75, 85, 99) # Gray 600
TEXT_MUTED = (156, 163, 175) # Gray 400
PRIMARY = (5, 150, 105) # Emerald 600
PRIMARY_LIGHT = (209, 250, 229) # Emerald 50
DANGER = (220, 38, 38) # Red 600
DANGER_LIGHT = (254, 226, 226) # Red 50
WARNING = (217, 119, 6) # Amber 600
WARNING_LIGHT = (254, 243, 199) # Amber 50
WHITE = (255, 255, 255)
BORDER = (229, 231, 235) # Gray 200

def _get_font(size, bold=False):
    # Try different fallbacks
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

def draw_pill(draw, x, y, text, bg_color, text_color, font, pad_x=20, pad_y=10):
    bbox = draw.textbbox((x, y), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    draw.rounded_rectangle([x, y, x + w + pad_x*2, y + h + pad_y*2], radius=(h + pad_y*2)//2, fill=bg_color)
    draw.text((x + pad_x, y + pad_y - 2), text, fill=text_color, font=font)
    return w + pad_x*2, h + pad_y*2

def draw_card(draw, box, fill=WHITE, outline=BORDER, radius=24, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def generate_preview():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_title = _get_font(52, True)
    f_sub = _get_font(32, False)
    f_h1 = _get_font(86, True)
    f_h2 = _get_font(42, True)
    f_h3 = _get_font(36, True)
    f_body = _get_font(32, False)
    f_small = _get_font(26, False)
    f_bold = _get_font(32, True)

    # --- Header ---
    draw.rectangle([0, 0, WIDTH, 160], fill=PRIMARY)
    draw.text((80, 45), "VidyutMitra", fill=WHITE, font=f_title)
    
    pill_w, _ = draw_pill(draw, WIDTH - 260, 55, "MESCOM BILL", (255,255,255, 50), WHITE, f_sub)

    # --- Top Impact Metric ---
    y = 220
    draw.text((80, y), "Net Bill Amount", fill=TEXT_SECONDARY, font=f_body)
    draw.text((80, y + 45), "Rs. 1,943", fill=TEXT_MAIN, font=f_h1)
    
    # Context Pill
    draw_pill(draw, 500, y + 80, "210 units consumed", PRIMARY_LIGHT, PRIMARY, f_small, pad_x=16, pad_y=8)
    draw_pill(draw, 750, y + 80, "3 kW load", (243, 244, 246), TEXT_SECONDARY, f_small, pad_x=16, pad_y=8)

    y += 180

    # --- Insights Grid ---
    # Fix Charge Trap Alert
    box1 = [80, y, WIDTH - 80, y + 220]
    draw_card(draw, box1, fill=WARNING_LIGHT, outline=WARNING, width=2)
    draw.text((120, y + 40), "⚠ FCT Alert: Sanctioned Load Over-Provisioned", fill=WARNING, font=f_h3)
    draw.text((120, y + 100), "Your 3 kW load is higher than your estimated 1.5 kW peak usage.", fill=TEXT_MAIN, font=f_body)
    draw.text((120, y + 150), "Reducing to 2 kW saves: Rs. 145 / mo (Rs. 1,740 / year)", fill=TEXT_MAIN, font=f_bold)
    
    y += 260

    # Solar ROI Widget
    box2 = [80, y, WIDTH - 80, y + 420]
    draw_card(draw, box2)
    draw.text((120, y + 45), "☀ Solar Opportunity", fill=TEXT_MAIN, font=f_h2)
    
    draw.line([120, y + 110, WIDTH - 120, y + 110], fill=BORDER, width=2)
    
    # 2 columns layout inside card
    col1 = 120
    col2 = 540
    
    draw.text((col1, y + 150), "Recommended System", fill=TEXT_SECONDARY, font=f_small)
    draw.text((col1, y + 190), "3 kW", fill=TEXT_MAIN, font=f_h3)

    draw.text((col2, y + 150), "Net Cost (Post Subsidy)", fill=TEXT_SECONDARY, font=f_small)
    draw.text((col2, y + 190), "Rs. 87,000", fill=TEXT_MAIN, font=f_h3)

    draw.text((col1, y + 270), "Estimated Payback", fill=TEXT_SECONDARY, font=f_small)
    draw.text((col1, y + 310), "3.8 Years", fill=PRIMARY, font=f_h3)

    draw.text((col2, y + 270), "25-Yr Savings", fill=TEXT_SECONDARY, font=f_small)
    draw.text((col2, y + 310), "~Rs. 3.2 Lakh", fill=PRIMARY, font=f_h3)
    
    y += 460

    # --- Footer ---
    draw.rectangle([0, HEIGHT - 100, WIDTH, HEIGHT], fill=(17, 24, 39))
    draw.text((80, HEIGHT - 65), "Data via KERC Tariff Order 2025 · CEA Database v21.0 · PM Surya Ghar", fill=(156, 163, 175), font=f_small)

    img.save("preview_design.png")
    print("Preview generated as preview_design.png")

if __name__ == "__main__":
    generate_preview()
