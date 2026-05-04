"""Unit tests for CSPAQ22200 (현물계좌예수금 주문가능금액 총평가2 조회).

Covers:
    - blocks.py — Pydantic OutBlock2 validation, including the new
      ``RcvblUablOrdAbleAmt`` field added by LS on 2026-04-10.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from programgarden_finance.ls.korea_stock.accno.CSPAQ22200.blocks import (
    CSPAQ22200OutBlock2,
)


# ---------------------------------------------------------------------------
# 1. blocks.py — RcvblUablOrdAbleAmt regression guard (LS 2026-04-10 update)
# ---------------------------------------------------------------------------


class TestCSPAQ22200OutBlock2RcvblUablOrdAbleAmt:
    """Regression guard for the LS 2026-04-10 schema update."""

    def test_field_present_in_schema(self):
        assert "RcvblUablOrdAbleAmt" in CSPAQ22200OutBlock2.model_fields

    def test_default_is_zero_int(self):
        out = CSPAQ22200OutBlock2()
        assert out.RcvblUablOrdAbleAmt == 0
        assert isinstance(out.RcvblUablOrdAbleAmt, int)

    def test_decodes_official_example_value(self):
        out = CSPAQ22200OutBlock2.model_validate({"RcvblUablOrdAbleAmt": 306})
        assert out.RcvblUablOrdAbleAmt == 306

    def test_field_position_after_CslLoanAmtdt1(self):
        names = list(CSPAQ22200OutBlock2.model_fields.keys())
        idx_csl = names.index("CslLoanAmtdt1")
        idx_new = names.index("RcvblUablOrdAbleAmt")
        assert idx_new == idx_csl + 1

    def test_description_audit_trail(self):
        desc = CSPAQ22200OutBlock2.model_fields["RcvblUablOrdAbleAmt"].description or ""
        assert "2026-04-10" in desc, "Audit trail (Added by LS ... date) missing"


# ---------------------------------------------------------------------------
# 2. Simplified validation (no official LS example for CSPAQ22200)
# ---------------------------------------------------------------------------


class TestCSPAQ22200OutBlock2OfficialExample:
    def test_with_new_field_validates(self):
        out = CSPAQ22200OutBlock2.model_validate({
            "CslLoanAmtdt1": 0,
            "RcvblUablOrdAbleAmt": 306,
        })
        assert out.RcvblUablOrdAbleAmt == 306
        assert out.CslLoanAmtdt1 == 0


# ---------------------------------------------------------------------------
# 3. Field examples auto-validation
# ---------------------------------------------------------------------------


class TestRcvblUablOrdAbleAmtExamples:
    """All values in ``examples=[...]`` must validate against the field type."""

    def test_examples_validate_against_field_type(self):
        for block_cls in (CSPAQ22200OutBlock2,):
            info = block_cls.model_fields["RcvblUablOrdAbleAmt"]
            adapter = TypeAdapter(info.annotation)
            for ex in info.examples or []:
                adapter.validate_python(ex)
