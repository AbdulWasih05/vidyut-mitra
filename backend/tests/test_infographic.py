"""Smoke tests for output.infographic — Pillow-drawn summary cards."""
from __future__ import annotations

import os

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA
from backend.output.infographic import render_infographic, render_to_temp_file

pytestmark = pytest.mark.smoke


def _persona_extraction(persona) -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-03-15",
        billing_period_days=persona.billing_period_days,
        sanctioned_load_kw=persona.sanctioned_load_kw,
        units_consumed=persona.units_consumed,
        subtotal_1_before_subsidy=persona.expected_subtotal_1,
        net_bill_amount=persona.expected_net_bill,
        is_gruha_jyothi_beneficiary=persona.is_gj_beneficiary,
        historical_avg_baseline=persona.gj_historical_avg_units,
        entitlement_units=persona.gj_entitlement_units,
        gruha_jyothi_subsidy_amount=(
            persona.expected_subtotal_1 if persona.is_gj_beneficiary else None
        ),
        gjs_registration_date="2023-08-26" if persona.is_gj_beneficiary else None,
    )


def _koppala_extraction() -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-04-10",
        billing_period_days=31,
        sanctioned_load_kw=2.0,
        units_consumed=390,
        subtotal_1_before_subsidy=3044.18,
        net_bill_amount=3044.18,
        is_gruha_jyothi_beneficiary=True,
        historical_avg_baseline=57.0,
        entitlement_units=63.0,
        gruha_jyothi_subsidy_amount=0.0,
        gjs_registration_date="2023-07-25",
    )


class TestRenderInfographic:
    def test_nikhil_non_gj_returns_png_bytes(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        png = render_infographic(_persona_extraction(NIKHIL), r)
        assert isinstance(png, bytes)
        assert len(png) > 1_000          # trivial smoke check
        # PNG signature: 89 50 4E 47 0D 0A 1A 0A
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_sunita_non_gj_renders(self):
        r = analyze_bill(_persona_extraction(SUNITA))
        png = render_infographic(_persona_extraction(SUNITA), r)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_priya_gj_under_entitlement_renders(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        png = render_infographic(_persona_extraction(PRIYA), r)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_koppala_cliff_crossed_renders(self):
        ext = _koppala_extraction()
        r = analyze_bill(ext)
        png = render_infographic(ext, r)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_image_dimensions_are_standard_card_size(self):
        from PIL import Image
        import io
        r = analyze_bill(_persona_extraction(NIKHIL))
        png = render_infographic(_persona_extraction(NIKHIL), r)
        img = Image.open(io.BytesIO(png))
        assert img.size == (1080, 1350)


class TestRenderToTempFile:
    def test_writes_png_and_returns_path(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        path = render_to_temp_file(_persona_extraction(NIKHIL), r)
        try:
            assert os.path.exists(path)
            assert path.endswith(".png")
            with open(path, "rb") as f:
                header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
