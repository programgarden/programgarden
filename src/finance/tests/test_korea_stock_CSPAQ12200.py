"""Unit tests for CSPAQ12200 (현물계좌예수금 주문가능금액 총평가 조회).

Covers:
    - blocks.py — Pydantic OutBlock2 validation, including:
        * the ``RcvblUablOrdAbleAmt`` field added by LS on 2026-04-11
          (originally announced for 2026-04-10 17:00 KST, then rescheduled
          to 2026-04-11 12:00 KST).
        * the ``MgnRat100pctOrdAbleAmt`` semantic change applied by LS on
          the same 2026-04-11 12:00 KST window — the field now exposes
          미수주문 가능 금액 (credit-eligible order-able amount); the legacy
          증거금률 100% 주문가능 금액 has moved to ``RcvblUablOrdAbleAmt``.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import TypeAdapter

from programgarden_finance.ls.korea_stock.accno.CSPAQ12200.blocks import (
    CSPAQ12200OutBlock2,
)


# ---------------------------------------------------------------------------
# 1. blocks.py — RcvblUablOrdAbleAmt regression guard (LS 2026-04-11 update)
# ---------------------------------------------------------------------------


class TestCSPAQ12200OutBlock2RcvblUablOrdAbleAmt:
    """Regression guard for the LS 2026-04-11 schema update."""

    def test_field_present_in_schema(self):
        assert "RcvblUablOrdAbleAmt" in CSPAQ12200OutBlock2.model_fields

    def test_default_is_zero_int(self):
        out = CSPAQ12200OutBlock2()
        assert out.RcvblUablOrdAbleAmt == 0
        assert isinstance(out.RcvblUablOrdAbleAmt, int)

    def test_decodes_official_example_value(self):
        out = CSPAQ12200OutBlock2.model_validate({"RcvblUablOrdAbleAmt": 306})
        assert out.RcvblUablOrdAbleAmt == 306

    def test_field_position_after_DpslRestrcAmt(self):
        names = list(CSPAQ12200OutBlock2.model_fields.keys())
        idx_dpsl = names.index("DpslRestrcAmt")
        idx_new = names.index("RcvblUablOrdAbleAmt")
        assert idx_new == idx_dpsl + 1

    def test_description_audit_trail_2026_04_11(self):
        """LS rescheduled the rollout from 2026-04-10 17:00 to 2026-04-11 12:00 KST."""
        desc = CSPAQ12200OutBlock2.model_fields["RcvblUablOrdAbleAmt"].description or ""
        assert "2026-04-11" in desc, "Audit trail (Added by LS ... date) must show 2026-04-11"
        assert "2026-04-10" not in desc, (
            "The 2026-04-10 date was the original (cancelled) rollout date and "
            "must not appear in the description; LS rescheduled to 2026-04-11."
        )

    def test_description_documents_legacy_migration(self):
        """The new field replaces the legacy 증거금률 100% semantic of MgnRat100pctOrdAbleAmt."""
        desc = CSPAQ12200OutBlock2.model_fields["RcvblUablOrdAbleAmt"].description or ""
        assert "MgnRat100pctOrdAbleAmt" in desc, (
            "Description must reference the legacy field that previously carried the "
            "증거금률 100% semantic so callers know to migrate."
        )


# ---------------------------------------------------------------------------
# 2. blocks.py — MgnRat100pctOrdAbleAmt semantic-change guard (LS 2026-04-11)
# ---------------------------------------------------------------------------


class TestCSPAQ12200OutBlock2MgnRat100pctOrdAbleAmtSemantic:
    """Regression guard for the LS 2026-04-11 semantic flip on MgnRat100pctOrdAbleAmt.

    LS Securities rotated the meaning of this field on 2026-04-11 12:00 KST:

      Before: 증거금률 100% 주문가능 금액 (100% margin-rate order-able amount)
      After:  미수주문 가능 금액 (credit/missed-payment-eligible order-able amount)

    The legacy semantic moved to ``RcvblUablOrdAbleAmt``. Description must
    explain both the old and new meaning so AI workflow generators do not
    reuse the pre-2026-04-11 mental model.
    """

    def test_field_still_present(self):
        assert "MgnRat100pctOrdAbleAmt" in CSPAQ12200OutBlock2.model_fields

    def test_default_is_zero_int(self):
        out = CSPAQ12200OutBlock2()
        assert out.MgnRat100pctOrdAbleAmt == 0
        assert isinstance(out.MgnRat100pctOrdAbleAmt, int)

    def test_description_documents_semantic_change_date(self):
        desc = CSPAQ12200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        assert "2026-04-11" in desc, (
            "Description must record the semantic-change effective date (2026-04-11)."
        )

    def test_description_documents_old_and_new_semantic(self):
        desc = CSPAQ12200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        # Old semantic must be acknowledged so callers understand the migration.
        assert "증거금률 100%" in desc or "증거금률 100 %" in desc, (
            "Description must reference the previous 증거금률 100% semantic."
        )
        # New semantic must be present.
        assert "미수주문" in desc, (
            "Description must reference the new 미수주문 semantic."
        )

    def test_description_points_to_replacement_field(self):
        desc = CSPAQ12200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        assert "RcvblUablOrdAbleAmt" in desc, (
            "Description must point migrating callers to RcvblUablOrdAbleAmt."
        )


# ---------------------------------------------------------------------------
# 3. LS official example response — full model_validate
# ---------------------------------------------------------------------------


class TestCSPAQ12200OutBlock2OfficialExample:
    """LS official example response data (per LS notice) full validation."""

    OFFICIAL_EXAMPLE: Dict[str, Any] = {
        "RecCnt": 1,
        "BrnNm": "다이렉트203",
        "AcntNm": "엘에스",
        "MnyOrdAbleAmt": 307,
        "MnyoutAbleAmt": 307,
        "BalEvalAmt": 227989450,
        "RcvblAmt": 0,
        "DpsastTotamt": 227989757,
        "PnlRat": 1031.979979,
        "InvstOrgAmt": 0,
        "InvstPlAmt": 227989757,
        "Dps": 307,
        "SubstAmt": 142982800,
        "D1Dps": 307,
        "D2Dps": 307,
        "MgnMny": 0,
        "MgnSubst": 0,
        "SubstOrdAbleAmt": 142982800,
        "MgnRat100pctOrdAbleAmt": 306,
        "MgnRat35ordAbleAmt": 306,
        "MgnRat50ordAbleAmt": 306,
        "PrdaySellAdjstAmt": 0,
        "PrdayBuyAdjstAmt": 0,
        "CrdaySellAdjstAmt": 0,
        "CrdayBuyAdjstAmt": 0,
        "D1ovdRepayRqrdAmt": 0,
        "D2ovdRepayRqrdAmt": 0,
        "Imreq": 0,
        "CrdtPldgRuseAmt": 0,
        "DpslRestrcAmt": 0,
        "RcvblUablOrdAbleAmt": 306,
        "SeOrdAbleAmt": 306,
        "KdqOrdAbleAmt": 306,
    }

    def test_official_example_validates(self):
        out = CSPAQ12200OutBlock2.model_validate(self.OFFICIAL_EXAMPLE)
        assert out.RcvblUablOrdAbleAmt == 306
        assert out.DpslRestrcAmt == 0
        assert out.MnyOrdAbleAmt == 307

    def test_legacy_and_new_fields_decode_independently(self):
        """In the post-2026-04-11 example, both fields hold the same value
        (306) only because the example happens to have 미수주문 가능 금액
        equal to the legacy 증거금률 100% 주문가능 금액. The schema must still
        keep the two fields independent (no field aliasing)."""
        out = CSPAQ12200OutBlock2.model_validate(self.OFFICIAL_EXAMPLE)
        assert out.MgnRat100pctOrdAbleAmt is not out.RcvblUablOrdAbleAmt or True  # tautology guard
        # Independent override sanity-check
        out2 = CSPAQ12200OutBlock2.model_validate({
            "MgnRat100pctOrdAbleAmt": 111,
            "RcvblUablOrdAbleAmt": 222,
        })
        assert out2.MgnRat100pctOrdAbleAmt == 111
        assert out2.RcvblUablOrdAbleAmt == 222


# ---------------------------------------------------------------------------
# 4. Field examples auto-validation
# ---------------------------------------------------------------------------


class TestRcvblUablOrdAbleAmtExamples:
    """All values in ``examples=[...]`` must validate against the field type."""

    def test_examples_validate_against_field_type(self):
        for field_name in ("RcvblUablOrdAbleAmt", "MgnRat100pctOrdAbleAmt"):
            info = CSPAQ12200OutBlock2.model_fields[field_name]
            adapter = TypeAdapter(info.annotation)
            for ex in info.examples or []:
                adapter.validate_python(ex)
