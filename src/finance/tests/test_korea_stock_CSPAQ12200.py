"""Unit tests for CSPAQ12200 (현물계좌예수금 주문가능금액 총평가 조회).

Covers:
    - blocks.py — Pydantic OutBlock2 validation, including the new
      ``RcvblUablOrdAbleAmt`` field added by LS on 2026-04-10.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import TypeAdapter

from programgarden_finance.ls.korea_stock.accno.CSPAQ12200.blocks import (
    CSPAQ12200OutBlock2,
)


# ---------------------------------------------------------------------------
# 1. blocks.py — RcvblUablOrdAbleAmt regression guard (LS 2026-04-10 update)
# ---------------------------------------------------------------------------


class TestCSPAQ12200OutBlock2RcvblUablOrdAbleAmt:
    """Regression guard for the LS 2026-04-10 schema update."""

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

    def test_description_audit_trail(self):
        desc = CSPAQ12200OutBlock2.model_fields["RcvblUablOrdAbleAmt"].description or ""
        assert "2026-04-10" in desc, "Audit trail (Added by LS ... date) missing"


# ---------------------------------------------------------------------------
# 2. LS official example response — full model_validate
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


# ---------------------------------------------------------------------------
# 3. Field examples auto-validation
# ---------------------------------------------------------------------------


class TestRcvblUablOrdAbleAmtExamples:
    """All values in ``examples=[...]`` must validate against the field type."""

    def test_examples_validate_against_field_type(self):
        for block_cls in (CSPAQ12200OutBlock2,):
            info = block_cls.model_fields["RcvblUablOrdAbleAmt"]
            adapter = TypeAdapter(info.annotation)
            for ex in info.examples or []:
                adapter.validate_python(ex)
