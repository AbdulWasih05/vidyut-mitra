"""Smoke tests for db/supabase_client.py.

All Supabase calls are mocked via ``FakeSupabaseClient`` — a minimal
in-memory double that mimics the chainable ``.table(...).select(...)...``
API. No real network hits.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

from backend.analysis.models import BillExtraction
from backend.db import supabase_client

pytestmark = pytest.mark.smoke


# =============================================================================
# FakeSupabaseClient — 80-line double of the Supabase chainable API
# =============================================================================


class _FakeResponse:
    def __init__(self, data: list[dict], count: int | None = None):
        self.data = data
        self.count = count


class _FakeQueryBuilder:
    def __init__(self, table_name: str, backing: dict[str, list[dict]]):
        self.table_name = table_name
        self.backing = backing
        self._filter: dict[str, Any] = {}
        self._op: str | None = None
        self._payload: Any = None

    def select(self, *_args: Any, count: Any = None):  # noqa: D401
        self._op = "select"
        return self

    def insert(self, data: dict):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data: dict):
        self._op = "update"
        self._payload = data
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col: str, val: Any):
        self._filter[col] = val
        return self

    def limit(self, _n: int):
        return self

    def _match(self, r: dict) -> bool:
        return all(r.get(k) == v for k, v in self._filter.items())

    def execute(self) -> _FakeResponse:
        rows = self.backing.setdefault(self.table_name, [])
        if self._op == "select":
            matching = [r for r in rows if self._match(r)]
            return _FakeResponse(matching, count=len(matching))
        if self._op == "insert":
            new = dict(self._payload)
            new.setdefault("id", str(uuid.uuid4()))
            rows.append(new)
            return _FakeResponse([new])
        if self._op == "update":
            matching = [r for r in rows if self._match(r)]
            for r in matching:
                r.update(self._payload)
            return _FakeResponse(matching)
        if self._op == "delete":
            matching = [r for r in rows if self._match(r)]
            if self.table_name == "users":
                # CASCADE bills — match DB schema's ON DELETE CASCADE.
                for m in matching:
                    uid = m.get("id")
                    self.backing["bills"] = [
                        b for b in self.backing.get("bills", []) if b.get("user_id") != uid
                    ]
            self.backing[self.table_name] = [r for r in rows if not self._match(r)]
            return _FakeResponse(matching)
        raise AssertionError(f"unknown op {self._op}")


class FakeSupabaseClient:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict]] = {"users": [], "bills": []}

    def table(self, name: str) -> _FakeQueryBuilder:
        return _FakeQueryBuilder(name, self._tables)

    # Escape hatches for test inspection.
    @property
    def users(self) -> list[dict]:
        return self._tables["users"]

    @property
    def bills(self) -> list[dict]:
        return self._tables["bills"]


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


@pytest.fixture
def nikhil_extraction() -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        consumer_name="NIKHIL SHETTY",
        rr_number="MNG-1234567",
        tariff_category="LT-1",
        billing_period_start="2026-02-15",
        billing_period_end="2026-03-15",
        billing_period_days=30,
        sanctioned_load_kw=3.0,
        previous_reading=45230,
        current_reading=45440,
        units_consumed=210,
        energy_charges=1218.0,
        fixed_charges=435.0,
        pg_surcharge=75.6,
        electricity_tax=109.62,
        fppca=105.0,
        other_charges=0.0,
        subtotal_1_before_subsidy=1943.22,
        is_gruha_jyothi_beneficiary=False,
        net_bill_amount=1943.22,
        extraction_confidence=0.91,
    )


# =============================================================================
# get_or_create_user / set_consent
# =============================================================================


class TestUsers:
    def test_get_or_create_creates_new_user_with_consent_false(self, fake_client):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        assert user["phone_number"] == "+919876543210"
        assert user["consent_given"] is False
        assert len(fake_client.users) == 1

    def test_get_or_create_returns_existing_row(self, fake_client):
        supabase_client.get_or_create_user("+919876543210", client=fake_client)
        again = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        assert len(fake_client.users) == 1
        assert again["phone_number"] == "+919876543210"

    def test_set_consent_true(self, fake_client):
        supabase_client.get_or_create_user("+919876543210", client=fake_client)
        updated = supabase_client.set_consent("+919876543210", True, client=fake_client)
        assert updated["consent_given"] is True

    def test_set_consent_creates_row_if_missing(self, fake_client):
        # START from a never-contacted number should still succeed.
        updated = supabase_client.set_consent("+918887776665", True, client=fake_client)
        assert updated["consent_given"] is True


# =============================================================================
# write_bill — DPDPA forbidden-field guards
# =============================================================================


class TestWriteBillDPDPA:
    def test_happy_path_writes_extracted_fields_only(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        bill_id = supabase_client.write_bill(
            user_id=user["id"],
            extraction=nikhil_extraction,
            analysis={"tariff_result": {"subtotal_1": 1943.22}, "solar_roi": {"payback_months": 45}},
            client=fake_client,
        )
        assert isinstance(bill_id, str)
        assert len(fake_client.bills) == 1
        row = fake_client.bills[0]
        assert row["units_consumed"] == 210
        assert row["subtotal_1"] == pytest.approx(1943.22)
        # DB uses is_gj_beneficiary column (short form).
        assert row["is_gj_beneficiary"] is False
        # Absence of any image-related column.
        for forbidden in ("bill_image", "bill_url", "image_bytes", "photo"):
            assert forbidden not in row

    def test_rejects_bill_image_kwarg(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        with pytest.raises(ValueError, match="Rule 2"):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis={},
                client=fake_client,
                bill_image=b"\x89PNG\r\n...",  # type: ignore[arg-type]
            )

    def test_rejects_bill_url_kwarg(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        with pytest.raises(ValueError):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis={},
                client=fake_client,
                bill_url="https://api.twilio.com/.../ME...",  # type: ignore[arg-type]
            )

    def test_rejects_forbidden_key_in_analysis_blob(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        with pytest.raises(ValueError, match="analysis blob"):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis={"bill_image_url": "https://api.twilio.com/.../ME..."},
                client=fake_client,
            )

    def test_analysis_must_be_dict(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        with pytest.raises(TypeError):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis="not a dict",  # type: ignore[arg-type]
                client=fake_client,
            )


# =============================================================================
# delete_user_cascade — hard delete + bill counts
# =============================================================================


class TestDeleteCascade:
    def test_delete_returns_true_and_zero_when_no_bills(self, fake_client):
        supabase_client.get_or_create_user("+919876543210", client=fake_client)
        existed, count = supabase_client.delete_user_cascade("+919876543210", client=fake_client)
        assert existed is True
        assert count == 0
        assert fake_client.users == []

    def test_delete_cascades_bills(self, fake_client, nikhil_extraction):
        user = supabase_client.get_or_create_user("+919876543210", client=fake_client)
        for _ in range(3):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis={},
                client=fake_client,
            )
        assert len(fake_client.bills) == 3
        existed, count = supabase_client.delete_user_cascade("+919876543210", client=fake_client)
        assert existed is True
        assert count == 3
        assert fake_client.bills == []   # CASCADE worked

    def test_delete_on_unknown_phone_returns_false_zero(self, fake_client):
        existed, count = supabase_client.delete_user_cascade("+910000000000", client=fake_client)
        assert existed is False
        assert count == 0


# =============================================================================
# language_preference get/set
# =============================================================================


class TestLanguagePreference:
    def test_get_on_unknown_phone_returns_none(self, fake_client):
        assert supabase_client.get_language_preference(
            "+910000000000", client=fake_client
        ) is None

    def test_get_on_user_without_preference_returns_none(self, fake_client):
        supabase_client.get_or_create_user("+919876543210", client=fake_client)
        assert supabase_client.get_language_preference(
            "+919876543210", client=fake_client
        ) is None

    def test_set_persists_language(self, fake_client):
        supabase_client.set_language_preference("+919876543210", "kn", client=fake_client)
        assert supabase_client.get_language_preference(
            "+919876543210", client=fake_client
        ) == "kn"

    def test_set_creates_row_if_missing(self, fake_client):
        # First contact may set language before any other write.
        supabase_client.set_language_preference("+918887776665", "en", client=fake_client)
        assert len(fake_client.users) == 1
        assert fake_client.users[0]["language_preference"] == "en"

    def test_set_can_flip_existing_preference(self, fake_client):
        supabase_client.set_language_preference("+919876543210", "kn", client=fake_client)
        supabase_client.set_language_preference("+919876543210", "en", client=fake_client)
        assert supabase_client.get_language_preference(
            "+919876543210", client=fake_client
        ) == "en"

    @pytest.mark.parametrize("bad", ["", "EN", "english", "hi", "ta", None, " kn "])
    def test_set_rejects_invalid_value(self, fake_client, bad):
        with pytest.raises(ValueError, match="language_preference"):
            supabase_client.set_language_preference(
                "+919876543210", bad, client=fake_client  # type: ignore[arg-type]
            )
