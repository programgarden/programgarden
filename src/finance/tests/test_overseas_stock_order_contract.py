"""Overseas stock order request contract (SPEC K5/K6/K7), offline.

The guide (apis[36].t[0]) lists OrdprcPtnCode 03/M3/M4 under "매도인경우 호가유형
확대": they are sell-only. A buy built with them is rejected before any request.
"""

import ast
from pathlib import Path

import pytest

from programgarden_finance.ls.overseas_stock.order.COSAT00301.blocks import (
    SELL_ONLY_PRICE_TYPE_CODES,
    COSAT00301InBlock1,
)
from programgarden_finance.ls.overseas_stock.order.COSAT00311.blocks import COSAT00311InBlock1

EXAMPLES = Path(__file__).parents[1] / "example/overseas_stock"


def block(**overrides):
    values = dict(OrdPtnCode="02", OrdMktCode="82", IsuNo="AAPL", OrdQty=1,
                  OvrsOrdPrc=1.0, OrdprcPtnCode="00")
    values.update(overrides)
    return COSAT00301InBlock1(**values)


@pytest.mark.parametrize("code", sorted(SELL_ONLY_PRICE_TYPE_CODES))
def test_buy_with_sell_only_price_type_is_rejected(code):
    with pytest.raises(ValueError) as error:
        block(OrdprcPtnCode=code)
    assert "매도인경우 호가유형 확대" in str(error.value)


@pytest.mark.parametrize("code", ["00", "M1", "M2"])
def test_buy_accepts_buy_price_types(code):
    assert block(OrdprcPtnCode=code).OrdprcPtnCode == code


@pytest.mark.parametrize("code", ["00", "03", "M1", "M2", "M3", "M4"])
def test_sell_accepts_every_documented_price_type(code):
    assert block(OrdPtnCode="01", OrdprcPtnCode=code).OrdprcPtnCode == code


def test_sell_only_set_matches_the_guide_wording():
    assert SELL_ONLY_PRICE_TYPE_CODES == frozenset({"03", "M3", "M4"})


def example_cancel_fields():
    tree = ast.parse((EXAMPLES / "run_COSAT00301_cancel.py").read_text())
    call, = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "COSAT00301InBlock1"]
    return {kw.arg: kw.value for kw in call.keywords}


def test_cancel_example_uses_the_verified_field_set():
    fields = example_cancel_fields()
    literal = {name: ast.literal_eval(value) for name, value in fields.items()
               if isinstance(value, ast.Constant)}
    assert set(fields) == {"RecCnt", "OrdPtnCode", "OrgOrdNo", "OrdMktCode", "IsuNo",
                           "OrdQty", "OvrsOrdPrc", "OrdprcPtnCode"}
    assert literal == {"RecCnt": 1, "OrdPtnCode": "08", "OrdQty": 0,
                       "OvrsOrdPrc": 0.0, "OrdprcPtnCode": "00"}
    cancel = COSAT00301InBlock1(RecCnt=1, OrdPtnCode="08", OrgOrdNo=12345, OrdMktCode="82",
                                IsuNo="AAPL", OrdQty=0, OvrsOrdPrc=0.0, OrdprcPtnCode="00")
    assert cancel.OrgOrdNo == 12345


def test_as4_example_reads_only_model_fields():
    from programgarden_finance.ls.overseas_stock.real.AS4.blocks import AS4RealResponseBody

    tree = ast.parse((EXAMPLES / "real_AS4.py").read_text())
    assignment, = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(getattr(t, "id", None) == "REJECT_FIELDS" for t in node.targets)]
    names = ast.literal_eval(assignment.value)
    assert "sRjtRsn" in names
    assert set(names) <= set(AS4RealResponseBody.model_fields)
    assert not {"sAcntNo", "sOrdAcntNo", "sAcntNm"} & set(names)


def test_modify_quantity_description_cites_guide_and_observation():
    description = COSAT00311InBlock1.model_fields["OrdQty"].description
    assert "0 입력" in description and "2026-09-24" in description
