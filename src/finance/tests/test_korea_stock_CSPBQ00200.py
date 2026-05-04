"""Unit tests for CSPBQ00200 (현물계좌 증거금률별 주문가능수량 조회).

Covers:
    - blocks.py — Pydantic OutBlock2 validation, focused on the LS
      2026-04-11 12:00 KST update (originally announced for 2026-04-10
      17:00 KST, then rescheduled to 2026-04-11). LS marked CSPBQ00200
      as "변경 only" — i.e., the ``MgnRat100pctOrdAbleAmt`` field's
      *semantic* changed but no new field was added on this TR. That
      asymmetry vs. CSPAQ12200/22200 (which got both the semantic flip
      AND a new ``RcvblUablOrdAbleAmt`` field) is part of the audit
      surface and must not silently regress.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import TypeAdapter

from programgarden_finance.ls.korea_stock.accno.CSPBQ00200.blocks import (
    CSPBQ00200OutBlock2,
)


# ---------------------------------------------------------------------------
# 1. blocks.py — MgnRat100pctOrdAbleAmt semantic-change guard (LS 2026-04-11)
# ---------------------------------------------------------------------------


class TestCSPBQ00200OutBlock2MgnRat100pctOrdAbleAmtSemantic:
    """Regression guard for the LS 2026-04-11 semantic flip.

    LS Securities rotated the meaning of this field on 2026-04-11 12:00 KST:

      Before: 증거금률 100% 주문가능 금액 (100% margin-rate order-able amount)
      After:  미수주문 가능 금액 (credit/missed-payment-eligible order-able amount)

    Unlike CSPAQ12200/22200, CSPBQ00200 did NOT receive a new
    ``RcvblUablOrdAbleAmt`` field — LS notice marks this TR as
    semantic-change only. Migrating callers needing the legacy
    증거금률 100% semantic must call CSPAQ12200/22200 instead.
    """

    def test_field_still_present(self):
        assert "MgnRat100pctOrdAbleAmt" in CSPBQ00200OutBlock2.model_fields

    def test_default_is_zero_int(self):
        out = CSPBQ00200OutBlock2()
        assert out.MgnRat100pctOrdAbleAmt == 0
        assert isinstance(out.MgnRat100pctOrdAbleAmt, int)

    def test_decodes_official_example_value(self):
        """Per LS notice example response, MgnRat100pctOrdAbleAmt = 79744009."""
        out = CSPBQ00200OutBlock2.model_validate({"MgnRat100pctOrdAbleAmt": 79744009})
        assert out.MgnRat100pctOrdAbleAmt == 79744009

    def test_description_documents_semantic_change_date(self):
        desc = CSPBQ00200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        assert "2026-04-11" in desc, (
            "Description must record the semantic-change effective date (2026-04-11)."
        )

    def test_description_documents_old_and_new_semantic(self):
        desc = CSPBQ00200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        assert "증거금률 100%" in desc or "증거금률 100 %" in desc, (
            "Description must reference the previous 증거금률 100% semantic."
        )
        assert "미수주문" in desc, (
            "Description must reference the new 미수주문 semantic."
        )

    def test_description_documents_cross_tr_migration_path(self):
        """CSPBQ00200 itself does not expose the legacy value — callers must
        cross-reference CSPAQ12200/22200 for ``RcvblUablOrdAbleAmt``."""
        desc = CSPBQ00200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"].description or ""
        assert "RcvblUablOrdAbleAmt" in desc, (
            "Description must point migrating callers to RcvblUablOrdAbleAmt."
        )
        assert "CSPAQ12200" in desc or "CSPAQ22200" in desc, (
            "Description must call out the cross-TR location of the legacy semantic "
            "since CSPBQ00200 itself does not carry it."
        )


# ---------------------------------------------------------------------------
# 2. CSPBQ00200 must NOT carry RcvblUablOrdAbleAmt (LS notice asymmetry)
# ---------------------------------------------------------------------------


class TestCSPBQ00200DoesNotAddRcvblUablOrdAbleAmt:
    """LS notice 2026-04-11 marks CSPBQ00200 as 변경-only (no field addition).

    This guards against accidentally porting the CSPAQ12200/22200 addition
    to CSPBQ00200, which would silently expose a field that LS does not
    actually return for this TR.
    """

    def test_field_not_in_schema(self):
        assert "RcvblUablOrdAbleAmt" not in CSPBQ00200OutBlock2.model_fields, (
            "LS notice 2026-04-11 explicitly marks CSPBQ00200 as semantic-change "
            "only; do not add RcvblUablOrdAbleAmt to this TR — LS does not "
            "expose it on CSPBQ00200's response."
        )


# ---------------------------------------------------------------------------
# 3. LS official example response — partial validation
#    (CSPBQ00200 OutBlock2 schema is intentionally narrower than the LS
#    response payload; pydantic ignores extras. We assert the fields we
#    do model decode correctly from the LS-published example.)
# ---------------------------------------------------------------------------


class TestCSPBQ00200OutBlock2OfficialExample:
    OFFICIAL_EXAMPLE: Dict[str, Any] = {
        "RecCnt": 1,
        "AcntNm": "우우돌",
        "IsuNm": "",
        "Dps": 80000000,
        "SubstAmt": 0,
        "MnyOrdAbleAmt": 79760000,
        "SubstOrdAbleAmt": 0,
        "MnyMgn": 240000,
        "SubstMgn": 0,
        "SeOrdAbleAmt": 265866666,
        "KdqOrdAbleAmt": 265866666,
        "MgnRat20pctOrdAbleAmt": 398800000,
        "MgnRat30pctOrdAbleAmt": 265866666,
        "MgnRat40pctOrdAbleAmt": 199400000,
        "MgnRat100pctOrdAbleAmt": 79744009,
        "MgnRat100MnyOrdAbleAmt": 79744009,
        "OrdAbleQty": 0,
        "OrdAbleAmt": 0,
    }

    def test_official_example_validates(self):
        out = CSPBQ00200OutBlock2.model_validate(self.OFFICIAL_EXAMPLE)
        # The semantic-flipped field decodes the LS-published value
        assert out.MgnRat100pctOrdAbleAmt == 79744009
        # Other margin-rate buckets remain stable
        assert out.MgnRat20pctOrdAbleAmt == 398800000
        assert out.MgnRat30pctOrdAbleAmt == 265866666
        assert out.MgnRat40pctOrdAbleAmt == 199400000
        # Account fields decode
        assert out.AcntNm == "우우돌"
        assert out.Dps == 80000000


# ---------------------------------------------------------------------------
# 4. Field examples auto-validation
# ---------------------------------------------------------------------------


class TestMgnRat100pctOrdAbleAmtExamples:
    """All values in ``examples=[...]`` must validate against the field type."""

    def test_examples_validate_against_field_type(self):
        info = CSPBQ00200OutBlock2.model_fields["MgnRat100pctOrdAbleAmt"]
        adapter = TypeAdapter(info.annotation)
        for ex in info.examples or []:
            adapter.validate_python(ex)
