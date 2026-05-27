"""Session 5.8 Commit 2 — Enhanced Level 2 cliff warning tests."""
from __future__ import annotations

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.analysis.subsidy_navigator import compute_gj_warnings
from backend.output.response_composer import compose_gj_response

pytestmark = pytest.mark.smoke


# =============================================================================
# compute_gj_warnings — enhanced Level 2 message content
# =============================================================================


def _warnings(units: int, entitlement: float = 100.0, subtotal: float = 1_800.0):
    return compute_gj_warnings(
        units_consumed=units,
        entitlement_units=entitlement,
        trailing_10m_avg=None,
        hypothetical_full_bill=subtotal,
    )


def _find(warnings, cliff):
    return next((w for w in warnings if w.cliff == cliff), None)


class TestLevel2Red:
    """>= 95% of 200 units — actionable RED warning."""

    def test_195_units_fires_red(self):
        ws = _warnings(195)
        w = _find(ws, "monthly_hard")
        assert w is not None and w.level == "red"

    def test_195_message_mentions_cut_5_units(self):
        w = _find(_warnings(195), "monthly_hard")
        assert "Cut 5 units" in w.message

    def test_195_message_has_cliff_alert_header(self):
        w = _find(_warnings(195), "monthly_hard")
        assert "Cliff Alert" in w.message

    def test_195_message_includes_hypothetical_bill_amount(self):
        w = _find(_warnings(195), "monthly_hard", )
        assert "Rs. 1,800" in w.message

    def test_195_message_has_behavior_prescription(self):
        w = _find(_warnings(195), "monthly_hard")
        assert "less fan" in w.message
        assert "less AC" in w.message
        assert "per day" in w.message

    def test_195_message_has_co2_framing(self):
        w = _find(_warnings(195), "monthly_hard")
        assert "CO2 avoided" in w.message
        assert "tree-days" in w.message


class TestLevel2Yellow:
    """80-94% of 200 units — softer YELLOW framing."""

    def test_180_units_fires_yellow(self):
        # 180/200 = 90% — that's still >= 95%? No, 0.90 < 0.95 → YELLOW.
        ws = _warnings(180)
        w = _find(ws, "monthly_hard")
        assert w is not None and w.level == "yellow"

    def test_180_message_has_watch_header(self):
        w = _find(_warnings(180), "monthly_hard")
        assert "Watch" in w.message

    def test_180_message_mentions_cut_20_units(self):
        w = _find(_warnings(180), "monthly_hard")
        assert "Cut 20 units" in w.message

    def test_180_message_includes_co2_in_kg(self):
        # 20 × 0.710 = 14.2 kg
        w = _find(_warnings(180), "monthly_hard")
        assert "14.2 kg" in w.message


class TestOver200Units:
    """KOPPALA class — already over the cap. Different message shape."""

    def test_390_units_message_says_over_cap(self):
        w = _find(_warnings(390, entitlement=63.0, subtotal=3_044.0), "monthly_hard")
        assert w is not None and w.level == "red"
        assert "OVER" in w.message or "over the 200-unit cap" in w.message.lower()

    def test_390_message_does_not_say_stay_safe(self):
        # Already crossed — no "To stay safe" phrasing.
        w = _find(_warnings(390, entitlement=63.0, subtotal=3_044.0), "monthly_hard")
        assert "stay safe" not in w.message.lower()
        assert "Cut " not in w.message   # no behavior prescription

    def test_390_message_mentions_entire_bill_payable(self):
        w = _find(_warnings(390, entitlement=63.0, subtotal=3_044.0), "monthly_hard")
        assert "entire" in w.message.lower()
        assert "3,044" in w.message


# =============================================================================
# Response composer integration — synthetic 180-unit GJ bill
# =============================================================================


def _gj_bill(units: int, entitlement: float, subtotal: float) -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-03-15",
        billing_period_days=30,
        sanctioned_load_kw=2.0,
        units_consumed=units,
        subtotal_1_before_subsidy=subtotal,
        is_gruha_jyothi_beneficiary=True,
        historical_avg_baseline=entitlement - 10,
        entitlement_units=entitlement,
        gruha_jyothi_subsidy_amount=subtotal,
        net_bill_amount=0.0,
        gjs_registration_date="2023-08-26",
    )


class TestComposerIntegration:
    def test_gj_180_units_response_has_cost_and_tree_days(self):
        # Under entitlement for GJ but close to the 200-unit hard cap.
        ext = _gj_bill(units=180, entitlement=200, subtotal=1_500.0)
        r = analyze_bill(ext)
        msg = compose_gj_response(r)
        # The enhanced Level 2 YELLOW text flows into the cliff section.
        assert "Watch" in msg or "Cliff" in msg
        assert "Cut" in msg
        assert "tree-days" in msg
        # Rupee cliff cost appears.
        assert "1,500" in msg or "1500" in msg
