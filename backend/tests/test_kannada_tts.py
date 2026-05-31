"""Smoke tests for output.kannada_tts + compose_kannada_voice_summary."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA
from backend.output import kannada_tts
from backend.output.kannada_tts import (
    DEFAULT_VOICE,
    FALLBACK_VOICE,
    synthesize_kannada,
    synthesize_to_temp_file,
)
from backend.output.response_composer import compose_kannada_voice_summary

pytestmark = pytest.mark.smoke


# =============================================================================
# Client initialization
# =============================================================================


class TestInitTtsClient:
    def test_raises_when_creds_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SARVAM_API_KEY", None)
            with pytest.raises(RuntimeError, match="SARVAM_API_KEY"):
                kannada_tts.init_tts_client(force_reload=True)


# =============================================================================
# synthesize_kannada — mocked Google TTS
# =============================================================================


def _fake_tts_client(audio_content: bytes = b"fake-ogg-bytes"):
    """Build a mock TextToSpeechClient whose synthesize_speech returns the
    given bytes."""
    client = MagicMock()
    client.synthesize_speech.return_value = MagicMock(audio_content=audio_content)
    return client


class TestSynthesize:
    def test_returns_audio_bytes(self):
        client = _fake_tts_client(b"OGG...Opus...bytes")
        result = synthesize_kannada("ನಮಸ್ಕಾರ", client=client)
        assert result == b"OGG...Opus...bytes"
        client.synthesize_speech.assert_called_once()

    def test_falls_back_to_standard_voice_on_wavenet_failure(self):
        client = MagicMock()
        # First call fails, second succeeds.
        client.synthesize_speech.side_effect = [
            RuntimeError("WaveNet unavailable"),
            MagicMock(audio_content=b"fallback-audio"),
        ]
        result = synthesize_kannada("ನಮಸ್ಕಾರ", client=client)
        assert result == b"fallback-audio"
        assert client.synthesize_speech.call_count == 2

    def test_no_infinite_recursion_when_fallback_also_fails(self):
        client = MagicMock()
        client.synthesize_speech.side_effect = RuntimeError("both voices down")
        with pytest.raises(RuntimeError, match="both voices down"):
            synthesize_kannada("ನಮಸ್ಕಾರ", client=client)


class TestSynthesizeToTempFile:
    def test_writes_ogg_file_and_returns_path(self, tmp_path):
        client = _fake_tts_client(b"\x4fggS-opus-audio")
        path = synthesize_to_temp_file("ನಮಸ್ಕಾರ", client=client)
        try:
            assert os.path.exists(path)
            assert path.endswith(".ogg")
            with open(path, "rb") as f:
                assert f.read() == b"\x4fggS-opus-audio"
        finally:
            kannada_tts.cleanup_media_file(path)

    def test_cleanup_media_file_does_not_raise_on_missing_path(self):
        kannada_tts.cleanup_media_file("/nonexistent/path.ogg")


# =============================================================================
# compose_kannada_voice_summary — three variants
# =============================================================================


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


class TestVoiceSummaryVariants:
    def test_nikhil_non_gj_mentions_solar_and_sanctioned_load(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        text = compose_kannada_voice_summary(_persona_extraction(NIKHIL), r)
        # Kannada greeting present.
        assert "ನಮಸ್ಕಾರ" in text
        # Bill amount appears (Nikhil net = 1943).
        assert "1,943" in text
        # Solar mentioned (English token for technical term).
        assert "Solar" in text or "solar" in text
        assert "ಯೂನಿಟ್" in text
        # Length cap per spec: ≤ 600 chars.
        assert len(text) <= 600

    def test_sunita_non_gj_has_fct_finding(self):
        r = analyze_bill(_persona_extraction(SUNITA))
        text = compose_kannada_voice_summary(_persona_extraction(SUNITA), r)
        # Sunita's FCT fires → finding should mention fixed charge.
        assert "fixed charge" in text.lower() or "sanctioned" in text.lower()

    def test_priya_under_entitlement_mentions_subsidy(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        text = compose_kannada_voice_summary(_persona_extraction(PRIYA), r)
        # Kannada word for Gruha Jyothi.
        assert "ಗೃಹ ಜ್ಯೋತಿ" in text
        # Subsidy rupee amount (Priya gets full subtotal = 1,080).
        assert "1,080" in text
        # ≤ 600 chars.
        assert len(text) <= 600

    def test_koppala_cliff_crossed_mentions_loss(self):
        ext = _koppala_extraction()
        r = analyze_bill(ext)
        text = compose_kannada_voice_summary(ext, r)
        # Units crossed 200.
        assert "200" in text
        # Kannada word for "lost" (ನಷ್ಟ).
        assert "ನಷ್ಟ" in text
        # Orchestrator re-computes the full bill from first principles — that's
        # 390 × 5.80 + 2 × 145 + 390 × 0.36 + 9% × 2262 + 390 × 0.50 ≈ Rs. 3,091.
        # (Differs from the extracted 3044 by the FPPCA placeholder delta,
        # which is expected — same behaviour seen in the text composer.)
        assert "3,091" in text
        assert len(text) <= 600

    def test_all_variants_end_with_whatsapp_followup_hint(self):
        for persona in (NIKHIL, PRIYA, SUNITA):
            r = analyze_bill(_persona_extraction(persona))
            text = compose_kannada_voice_summary(_persona_extraction(persona), r)
            # Every variant directs to the WhatsApp text for full details.
            assert "WhatsApp" in text
