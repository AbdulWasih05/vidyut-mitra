"""Tests for the Groq-backed AI composer.

The Groq client is always mocked — these tests don't make network calls.
We verify:
- FactPack shape per persona (Nikhil/Sunita/Priya all expose the right keys)
- Validator correctly accepts verbatim numbers and rejects paraphrased ones
- Public APIs return None on every Groq failure mode (caller falls back)
- Public APIs return AILines / AIFollowupLine on the happy path
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA
from backend.output import ai_composer
from backend.output.ai_composer import (
    AIFollowupLine,
    AILines,
    build_followup_factpack,
    build_main_factpack,
    compose_followup_line,
    compose_main_lines,
    validate_ai_output,
)

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


# =============================================================================
# Fact-pack shape — one test per persona to lock the field contract.
# =============================================================================


class TestFactPackNikhil:
    """Non-GJ + FCT fires + solar-eligible → fc, fa, fr, se, sm, sp present."""

    @pytest.fixture
    def pack(self):
        result = analyze_bill(_persona_extraction(NIKHIL))
        return build_main_factpack(result)

    def test_units_match(self, pack):
        assert pack["u"] == 210

    def test_load_match(self, pack):
        assert pack["l"] == 3

    def test_not_gj(self, pack):
        assert pack["g"] == 0
        assert "ge" not in pack
        assert "subM" not in pack

    def test_fct_fields_present(self, pack):
        assert pack["fc"] == 1
        assert pack["fa"] == 1740      # load-bearing pitch number
        assert pack["fr"] == 2

    def test_solar_fields_present(self, pack):
        assert pack["se"] == 1
        assert pack["ss"] == 78_000


class TestFactPackPriya:
    """GJ + Level 0 RED warning → ge, ent, uPct, warn, buf present."""

    @pytest.fixture
    def pack(self):
        result = analyze_bill(_persona_extraction(PRIYA))
        return build_main_factpack(result)

    def test_is_gj(self, pack):
        assert pack["g"] == 1
        assert pack["ge"] == 1

    def test_entitlement_is_115(self, pack):
        # Briefing rule: min(105 + 10, 200) = 115. Hard guard against the
        # 200-units copy-paste error called out in CLAUDE.md Rule 1.
        assert pack["ent"] == 115

    def test_utilization_about_96_pct(self, pack):
        # 110/115 = 95.65 → rounds to 96.
        assert pack["uPct"] == 96

    def test_buffer_is_5_units(self, pack):
        # Priya at 110/115 — soft step is closer (5 units to entitlement)
        # than the 200-unit hard cap (90 units away).
        assert pack["buf"] == 5
        assert pack["bk"] == "soft"

    def test_approaching_warning_present(self, pack):
        # Level 0 fires for Priya; CLAUDE.md flags this as load-bearing for
        # the GJ Visibility demo moment.
        assert pack["warn"] == "approaching_entitlement"

    def test_fct_does_not_fire(self, pack):
        # 2 kW sanctioned, peak under threshold — FCT must not fire.
        assert "fc" not in pack


class TestBufClosestCliff:
    """Option A: buf reports the SMALLEST positive distance to a pending cliff,
    tagged with bk ('soft' = personal entitlement, 'hard' = 200-cap, 'past' =
    already over 200). This avoids the headline/template contradiction where
    one section talked about Cliff 1 and the other about Cliff 2."""

    def _build_factpack(self, units, entitlement):
        ext = BillExtraction(
            is_mescom_bill=True, tariff_category='LT-1',
            billing_period_end='2026-03-15', billing_period_days=30,
            sanctioned_load_kw=2.0, units_consumed=units,
            subtotal_1_before_subsidy=1000.0, net_bill_amount=0.0,
            is_gruha_jyothi_beneficiary=True,
            historical_avg_baseline=entitlement - 10,
            entitlement_units=entitlement,
            gruha_jyothi_subsidy_amount=1000.0,
            gjs_registration_date='2023-08-26',
        )
        return build_main_factpack(analyze_bill(ext))

    def test_below_entitlement_picks_soft(self):
        # 110 units, entitlement 115 → buf_soft=5, buf_hard=90 → soft wins
        pack = self._build_factpack(units=110, entitlement=115)
        assert pack["buf"] == 5
        assert pack["bk"] == "soft"

    def test_above_entitlement_below_200_picks_hard(self):
        # 170 units, entitlement 123 → soft already crossed (-47), hard=30 → hard wins
        pack = self._build_factpack(units=170, entitlement=123)
        assert pack["buf"] == 30
        assert pack["bk"] == "hard"

    def test_well_below_both_picks_soft_when_smaller(self):
        # 50 units, entitlement 100 → buf_soft=50, buf_hard=150 → soft is closer
        pack = self._build_factpack(units=50, entitlement=100)
        assert pack["buf"] == 50
        assert pack["bk"] == "soft"

    def test_above_both_reports_past(self):
        # 250 units, entitlement 123 → both crossed → past
        pack = self._build_factpack(units=250, entitlement=123)
        assert pack["buf"] == 0
        assert pack["bk"] == "past"


class TestFactPackSunita:
    """High consumption → solar fields with bigger payback than Nikhil."""

    @pytest.fixture
    def pack(self):
        result = analyze_bill(_persona_extraction(SUNITA))
        return build_main_factpack(result)

    def test_units_280(self, pack):
        assert pack["u"] == 280

    def test_solar_payback_faster_than_nikhil(self, pack):
        # Sunita ~3.2 yr, Nikhil ~3.8 yr.
        nikhil = build_main_factpack(analyze_bill(_persona_extraction(NIKHIL)))
        assert pack["sp"] < nikhil["sp"]


# =============================================================================
# Validator behaviour.
# =============================================================================


class TestValidator:
    def test_accepts_verbatim_rupee_amount(self):
        pack = {"u": 210, "fa": 1740}
        text = "👉 You're paying Rs. 1,740/year for unused capacity (210 units)."
        assert validate_ai_output(text, pack) is True

    def test_rejects_paraphrased_amount(self):
        pack = {"u": 210, "fa": 1740}
        # AI rounded 1,740 → 1,700. Must reject.
        text = "👉 You're paying around Rs. 1,700/year extra."
        assert validate_ai_output(text, pack) is False

    def test_rejects_hallucinated_constant(self):
        # Classic Rule 1 hallucination: stale CO2 factor 0.727. Must reject.
        pack = {"sc": 2.98}
        text = "👉 CO2 factor: 0.727 kg/kWh, you save 2.98 tonnes/year."
        assert validate_ai_output(text, pack) is False

    def test_allows_trivial_numbers(self):
        pack = {"u": 210}
        # "1" and "2" are list/count nouns — not factual claims.
        text = "👉 1 quick fix — reduce to 2 kW for 210 units."
        assert validate_ai_output(text, pack) is True

    def test_accepts_decimal_match(self):
        pack = {"sp": 3.8}
        text = "👉 Payback in 3.8 years."
        assert validate_ai_output(text, pack) is True

    def test_accepts_floor_form_of_decimal(self):
        # subM = 1080.02 — AI may write "Rs. 1,080" (floor). Allow.
        pack = {"subM": 1080.02}
        text = "👉 Subsidy: Rs. 1,080 this month."
        assert validate_ai_output(text, pack) is True

    def test_rejects_fabricated_zero(self):
        """Regression: AI was hallucinating "0 unit buffer" when buf was 30.
        '0' used to be in the trivial-numbers whitelist; removing it forces
        the AI to use real factpack values for zero claims too."""
        pack = {"u": 170, "ent": 200, "buf": 30}  # 30 buffer remaining
        text = "🚨 0 unit buffer — subsidy at risk!"
        assert validate_ai_output(text, pack) is False

    def test_accepts_zero_when_factpack_has_zero(self):
        """Priya-class users have b=0 (zero net bill). AI saying "Rs. 0" must pass."""
        pack = {"u": 110, "b": 0, "subM": 1080.02}
        text = "👉 Rs. 0 paid this month — Karnataka covered Rs. 1,080.02."
        assert validate_ai_output(text, pack) is True


# =============================================================================
# Public API — happy path + every failure mode falls back to None.
# =============================================================================


def _mock_groq_response(content: str) -> MagicMock:
    """Build a Groq client mock that returns a single message with `content`."""
    client = MagicMock()
    msg = MagicMock()
    msg.content = content
    choice = MagicMock(message=msg)
    completion = MagicMock(choices=[choice])
    client.chat.completions.create.return_value = completion
    return client


class TestComposeMainLines:
    @pytest.fixture
    def nikhil_result(self):
        return analyze_bill(_persona_extraction(NIKHIL))

    def test_returns_none_when_no_api_key(self, monkeypatch, nikhil_result):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        assert compose_main_lines(nikhil_result) is None

    def test_returns_lines_on_valid_response(self, nikhil_result):
        good = (
            '{"headline":"👉 You\'re paying Rs. 1,740/year extra in fixed charges.",'
            '"priority":"🎯 Start with: FIXED\\n   (small effort, sure savings)"}'
        )
        with patch.object(ai_composer, "_groq_client", return_value=_mock_groq_response(good)):
            lines = compose_main_lines(nikhil_result)
        assert isinstance(lines, AILines)
        assert "1,740" in lines.headline
        assert "FIXED" in lines.priority

    def test_falls_back_on_invalid_json(self, nikhil_result):
        with patch.object(ai_composer, "_groq_client", return_value=_mock_groq_response("not json")):
            assert compose_main_lines(nikhil_result) is None

    def test_falls_back_on_missing_fields(self, nikhil_result):
        partial = '{"headline":"👉 some text"}'  # priority missing
        with patch.object(ai_composer, "_groq_client", return_value=_mock_groq_response(partial)):
            assert compose_main_lines(nikhil_result) is None

    def test_falls_back_when_validator_rejects(self, nikhil_result):
        # AI hallucinates a number not in the FactPack (1700 vs 1740).
        bad = (
            '{"headline":"👉 You\'re paying Rs. 1,700/year extra in fixed charges.",'
            '"priority":"🎯 Start with: FIXED\\n   (small effort, sure savings)"}'
        )
        with patch.object(ai_composer, "_groq_client", return_value=_mock_groq_response(bad)):
            assert compose_main_lines(nikhil_result) is None

    def test_falls_back_when_groq_raises(self, nikhil_result):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("rate limited")
        with patch.object(ai_composer, "_groq_client", return_value=client):
            assert compose_main_lines(nikhil_result) is None


class TestComposeFollowupLine:
    @pytest.fixture
    def nikhil_result(self):
        return analyze_bill(_persona_extraction(NIKHIL))

    def test_followup_factpack_solar_includes_payback(self, nikhil_result):
        pack = build_followup_factpack(
            "SOLAR", _persona_extraction(NIKHIL), nikhil_result,
        )
        assert pack["topic"] == "solar"
        assert pack["u"] == 210
        assert "sp" in pack

    def test_returns_line_on_valid_response(self, nikhil_result):
        good = '{"context":"👉 At 210 units/month, your payback beats average."}'
        with patch.object(ai_composer, "_groq_client", return_value=_mock_groq_response(good)):
            line = compose_followup_line(
                "SOLAR", _persona_extraction(NIKHIL), nikhil_result,
            )
        assert isinstance(line, AIFollowupLine)
        assert "210" in line.context

    def test_returns_none_when_no_api_key(self, monkeypatch, nikhil_result):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        line = compose_followup_line(
            "SOLAR", _persona_extraction(NIKHIL), nikhil_result,
        )
        assert line is None
