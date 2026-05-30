"""Per-bill infographic \u2014 Pillow-drawn PNG summary card.

B&W Professional UX layout.
Session 6 priority 2. ``render_infographic(extraction, analysis)`` returns
PNG bytes; ``render_to_temp_file`` writes them to ``MEDIA_TMP_DIR`` so the
Twilio dispatcher can hand the public URL to WhatsApp.
"""
from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path
from typing import Any

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import AnalysisResult
from backend.output.kannada_tts import MEDIA_TMP_DIR

logger = logging.getLogger(__name__)

# Dimensions
WIDTH = 1080
HEIGHT = 1350

# B&W Palette
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_DARK = (60, 60, 60)
GRAY_MED = (120, 120, 120)
GRAY_LIGHT = (220, 220, 220)

def render_infographic(
    extraction: BillExtraction,
    analysis: AnalysisResult,
) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    f_title = _load_font(56, "bold")
    f_h1 = _load_font(100, "bold")
    f_h2 = _load_font(46, "bold")
    f_h3 = _load_font(36, "bold")
    f_body = _load_font(30, "regular")
    f_small_bold = _load_font(26, "bold")
    f_small = _load_font(26, "regular")
    f_tiny = _load_font(22, "regular")

    # --- Header ---
    draw.rectangle([0, 0, WIDTH, 120], fill=BLACK)
    draw.text((60, 30), "VidyutMitra", fill=WHITE, font=f_title)
    
    try:
        report_w = draw.textlength("MESCOM BILL REPORT", font=f_small_bold)
    except AttributeError:
        # Fallback for older Pillow
        bbox = draw.textbbox((0, 0), "MESCOM BILL REPORT", font=f_small_bold)
        report_w = bbox[2] - bbox[0]
    
    draw.text((WIDTH - 60 - report_w, 45), "MESCOM BILL REPORT", fill=WHITE, font=f_small_bold)

    y = 160
    units = extraction.units_consumed or 0
    is_gj = bool(extraction.is_gruha_jyothi_beneficiary)
    crossed_cliff = is_gj and units > 200

    fonts = {
        "h1": f_h1, "h2": f_h2, "h3": f_h3, "body": f_body, 
        "small_bold": f_small_bold, "small": f_small, "tiny": f_tiny
    }

    if is_gj and not crossed_cliff:
        y = _draw_gj_under_card(draw, y, extraction, analysis, fonts)
    elif crossed_cliff:
        y = _draw_gj_cliff_card(draw, y, extraction, analysis, fonts)
    else:
        y = _draw_non_gj_card(draw, y, extraction, analysis, fonts)

    # --- Footer ---
    y = HEIGHT - 80
    draw.text((60, y), "DATA SOURCE: KERC TARIFF ORDER 2025 | CEA DATABASE V21.0 | PM SURYA GHAR", fill=GRAY_MED, font=f_tiny)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_to_temp_file(
    extraction: BillExtraction,
    analysis: AnalysisResult,
) -> str:
    png_bytes = render_infographic(extraction, analysis)
    filename = f"card_{uuid.uuid4().hex[:12]}.png"
    filepath = MEDIA_TMP_DIR / filename
    filepath.write_bytes(png_bytes)
    return str(filepath)


def _draw_non_gj_card(draw: Any, y: int, extraction: BillExtraction, analysis: AnalysisResult, fonts: dict) -> int:
    roi = analysis.solar_roi
    fct = analysis.fct
    units = extraction.units_consumed or 0
    load = extraction.sanctioned_load_kw or 0.0

    # --- Main Metric ---
    draw.text((60, y), "NET BILL AMOUNT", fill=GRAY_MED, font=fonts["small_bold"])
    y += 40
    draw.text((60, y), f"Rs. {analysis.net_bill_amount:,.0f}", fill=BLACK, font=fonts["h1"])
    y += 140
    
    # Context split 
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 30
    draw.text((60, y), f"{units} UNITS CONSUMED", fill=BLACK, font=fonts["small_bold"])
    draw.text((450, y), f"{load:.0f} KW SANCTIONED LOAD", fill=BLACK, font=fonts["small_bold"])
    
    y += 60
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4) 
    y += 60

    # --- Fixed Charge Trap ---
    box1_y1 = y
    if fct.fires:
        box1_y2 = y + 260
        draw.rectangle([60, box1_y1, WIDTH - 60, box1_y2], outline=BLACK, width=6)
        draw.rectangle([60, box1_y1, WIDTH - 60, box1_y1 + 70], fill=BLACK)
        draw.text((90, box1_y1 + 18), "ATTENTION: SANCTIONED LOAD OVER-PROVISIONED", fill=WHITE, font=fonts["small_bold"])
        draw.text((90, box1_y1 + 100), f"Your {fct.sanctioned_load_kw:.0f} kW load is higher than your estimated {fct.estimated_peak_kw:.1f} kW peak usage.", fill=GRAY_DARK, font=fonts["body"])
        draw.text((90, box1_y1 + 155), "Recommended Action:", fill=GRAY_MED, font=fonts["small"])
        draw.text((90, box1_y1 + 195), f"Reduce to {fct.recommended_load_kw:.0f} kW to save Rs. {fct.excess_monthly_cost:.0f} / mo (Rs. {fct.excess_annual_cost:,.0f} / year)", fill=BLACK, font=fonts["h3"])
        y = box1_y2 + 80
    else:
        draw.text((60, y), "SANCTIONED LOAD IS OPTIMAL", fill=GRAY_MED, font=fonts["small_bold"])
        draw.text((60, y + 40), f"Your {load:.0f} kW load aligns with your peak usage.", fill=BLACK, font=fonts["h3"])
        y += 120

    # --- Solar ROI ---
    draw.text((60, y), "ROOFTOP SOLAR ROI", fill=BLACK, font=fonts["h2"])
    y += 70
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 40

    col1, col2 = 60, WIDTH // 2 + 20
    draw.text((col1, y), "RECOMMENDED SYSTEM", fill=GRAY_MED, font=fonts["small_bold"])
    draw.text((col1, y + 40), f"{roi.system_kw} kW", fill=BLACK, font=fonts["h3"])
    draw.text((col2, y), "NET COST (POST SUBSIDY)", fill=GRAY_MED, font=fonts["small_bold"])
    draw.text((col2, y + 40), f"Rs. {roi.net_cost:,.0f}", fill=BLACK, font=fonts["h3"])
    y += 120
    draw.text((col1, y), "ESTIMATED PAYBACK", fill=GRAY_MED, font=fonts["small_bold"])
    draw.text((col1, y + 40), f"{roi.payback_years} Years", fill=BLACK, font=fonts["h3"])
    draw.text((col2, y), "LIFETIME SAVINGS (25 YRS)", fill=GRAY_MED, font=fonts["small_bold"])
    draw.text((col2, y + 40), f"~Rs. {roi.lifetime_net_savings_flat / 1_00_000:.1f} Lakh", fill=BLACK, font=fonts["h3"])
    y += 120
    draw.text((col1, y), "CO2 AVOIDED", fill=GRAY_MED, font=fonts["small_bold"])
    draw.text((col1, y + 40), f"{roi.co2_offset_tonnes_per_year:.2f} tonnes / year", fill=BLACK, font=fonts["h3"])
    y += 120
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4)

    return y


def _draw_gj_under_card(draw: Any, y: int, extraction: BillExtraction, analysis: AnalysisResult, fonts: dict) -> int:
    gj = analysis.gj_visibility
    subsidy = gj.monthly_subsidy_received if gj else 0.0
    units = extraction.units_consumed or 0

    # --- Main Metric ---
    draw.text((60, y), "GRUHA JYOTHI SUBSIDY", fill=GRAY_MED, font=fonts["small_bold"])
    y += 40
    draw.text((60, y), f"Rs. {subsidy:,.0f} Paid On Your Behalf", fill=BLACK, font=fonts["h2"])
    y += 90
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 30
    draw.text((60, y), f"YOU PAID: RS. {analysis.net_bill_amount:,.0f}", fill=BLACK, font=fonts["h2"])
    y += 80
    draw.text((60, y), f"{units} of {gj.entitlement_units:.0f} entitled units used", fill=GRAY_DARK, font=fonts["body"])
    y += 80
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4)
    y += 60

    util_of_200 = (units / 200.0) * 100
    box1_y1 = y
    if util_of_200 >= 80:
        box1_y2 = y + 260
        draw.rectangle([60, box1_y1, WIDTH - 60, box1_y2], outline=BLACK, width=6)
        draw.rectangle([60, box1_y1, WIDTH - 60, box1_y1 + 70], fill=BLACK)
        draw.text((90, box1_y1 + 18), "WARNING: APPROACHING 200-UNIT CLIFF", fill=WHITE, font=fonts["small_bold"])
        draw.text((90, box1_y1 + 100), f"You have used {units}/200 units ({util_of_200:.0f}%).", fill=GRAY_DARK, font=fonts["body"])
        draw.text((90, box1_y1 + 155), "Penalty Risk:", fill=GRAY_MED, font=fonts["small"])
        draw.text((90, box1_y1 + 195), "Crossing 200 loses the entire subsidy this month", fill=BLACK, font=fonts["h3"])
        y = box1_y2 + 80
    else:
        draw.text((60, y), "STATUS: SAFELY BELOW CAP", fill=GRAY_MED, font=fonts["small_bold"])
        draw.text((60, y + 40), f"{units}/200 units ({util_of_200:.0f}%)", fill=BLACK, font=fonts["h3"])
        y += 120

    if gj and gj.estimated_total_subsidy_received:
        draw.text((60, y), "LIFETIME SUBSIDY RECEIVED", fill=GRAY_MED, font=fonts["small_bold"])
        draw.text((60, y + 40), f"~Rs. {gj.estimated_total_subsidy_received:,.0f}", fill=BLACK, font=fonts["h3"])
        y += 120
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4)

    return y


def _draw_gj_cliff_card(draw: Any, y: int, extraction: BillExtraction, analysis: AnalysisResult, fonts: dict) -> int:
    units = extraction.units_consumed or 0

    # --- Main Metric ---
    draw.text((60, y), "SUBSIDY STATUS", fill=GRAY_MED, font=fonts["small_bold"])
    y += 40
    draw.text((60, y), "LOST THIS MONTH", fill=BLACK, font=fonts["h1"])
    y += 140
    
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 30
    draw.text((60, y), f"YOU CROSSED THE 200-UNIT CAP ({units} UNITS)", fill=BLACK, font=fonts["small_bold"])
    y += 60
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4) 
    y += 60

    # Red banner translated to B&W
    box1_y1 = y
    box1_y2 = y + 260
    draw.rectangle([60, box1_y1, WIDTH - 60, box1_y2], outline=BLACK, width=6)
    draw.rectangle([60, box1_y1, WIDTH - 60, box1_y1 + 70], fill=BLACK)
    draw.text((90, box1_y1 + 18), "ACTION REQUIRED: FULL BILL PAYABLE", fill=WHITE, font=fonts["small_bold"])
    draw.text((90, box1_y1 + 100), "Since your usage was over 200 units, the subsidy is dropped.", fill=GRAY_DARK, font=fonts["body"])
    draw.text((90, box1_y1 + 155), "Amount Due:", fill=GRAY_MED, font=fonts["small"])
    draw.text((90, box1_y1 + 195), f"Rs. {analysis.net_bill_amount:,.0f}", fill=BLACK, font=fonts["h3"])
    y = box1_y2 + 80

    draw.text((60, y), "PATH BACK TO RS. 0 NEXT MONTH", fill=BLACK, font=fonts["h2"])
    y += 70
    draw.line([60, y, WIDTH - 60, y], fill=GRAY_LIGHT, width=2)
    y += 40
    
    draw.text((60, y), "• Stay under 200 units \u2014 next month resets", fill=BLACK, font=fonts["h3"])
    y += 60
    draw.text((60, y), "• AC thermostat 24 \u00B0C, shorter geyser runs", fill=BLACK, font=fonts["h3"])
    y += 120
    draw.line([60, y, WIDTH - 60, y], fill=BLACK, width=4)

    return y


_FONT_CACHE: dict[tuple, Any] = {}

def _load_font(size: int, weight: str = "regular") -> Any:
    from PIL import ImageFont
    key = (size, weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates = [
        "DejaVuSans-Bold.ttf" if weight == "bold" else "DejaVuSans.ttf",
        "arialbd.ttf" if weight == "bold" else "arial.ttf",
        "segoeuib.ttf" if weight == "bold" else "segoeui.ttf",
        "Helvetica-Bold.ttf" if weight == "bold" else "Helvetica.ttf",
    ]
    for name in candidates:
        try:
            font = ImageFont.truetype(name, size)
            _FONT_CACHE[key] = font
            return font
        except (OSError, IOError):
            continue

    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font