"""Regressions for owner-provided LS contracts, without broker calls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from programgarden_finance.ls.korea_stock.accno.CSPAQ12300 import TrCSPAQ12300
from programgarden_finance.ls.korea_stock.accno.CSPAQ12300.blocks import (
    CSPAQ12300InBlock1, CSPAQ12300OutBlock2, CSPAQ12300OutBlock3,
    CSPAQ12300Request, CSPAQ12300Response,
)
from programgarden_finance.ls.korea_stock.accno.FOCCQ33600.blocks import (
    FOCCQ33600InBlock1, FOCCQ33600OutBlock1,
)


def load_example():
    path = Path(__file__).resolve().parents[1] / "example/korea_stock/run_CSPAQ12300.py"
    spec = importlib.util.spec_from_file_location("cspaq12300_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("balance", ["0", "1", "9"])
def test_official_balance_codes_and_example_record_count(balance):
    request = CSPAQ12300InBlock1(BalCreTp=balance)
    assert request.model_dump() == {
        "RecCnt": 1, "BalCreTp": balance, "CmsnAppTpCode": "0",
        "D2balBaseQryTp": "0", "UprcTpCode": "0",
    }


@pytest.mark.parametrize("field,value", [
    ("BalCreTp", "2"), ("BalCreTp", "3"), ("BalCreTp", "4"),
    ("BalCreTp", "5"), ("BalCreTp", "6"), ("CmsnAppTpCode", "2"),
    ("D2balBaseQryTp", "2"), ("UprcTpCode", "2"),
])
def test_codes_not_in_the_supplied_table_are_rejected(field, value):
    with pytest.raises(ValidationError):
        CSPAQ12300InBlock1(**{field: value})


def test_every_summary_field_exposes_unavailable_schema_metadata():
    schema = CSPAQ12300OutBlock2.model_json_schema()
    assert len(schema["properties"]) == 70  # 69 source fields + one legacy field.
    for name, prop in schema["properties"].items():
        assert prop["ls_availability"] == "not_provided", name
        assert "Not provided" in prop["description"], name
        assert "placeholders" in prop["description"], name
    assert schema["properties"]["EvalPnl"]["deprecated"] is True
    assert schema["properties"]["EvalPnl"]["ls_source_declared"] is False
    assert schema["properties"]["EvalPnlSum"]["ls_source_length"] == "15"


@pytest.mark.parametrize("placeholder", [0, 12345])
def test_summary_values_cannot_claim_availability_or_hide_position_evidence(placeholder):
    request = CSPAQ12300Request(body={"CSPAQ12300InBlock1": CSPAQ12300InBlock1()})
    result = TrCSPAQ12300(request)._build_response(
        SimpleNamespace(status=200),
        {
            "rsp_cd": "00136", "rsp_msg": "fixture",
            "CSPAQ12300OutBlock2": {"Dps": placeholder, "EvalPnlSum": placeholder},
            # Whitelisted owner example, not an observed live holding.
            "CSPAQ12300OutBlock3": [{
                "IsuNo": "A005930", "BalQty": 0, "BnsBaseBalQty": 1,
                "BuyUnsttQty": 1, "PchsAmt": 60000, "AvrUprc": "60000.00",
                "BalEvalAmt": 82700, "EvalPnl": 22700, "PnlRat": "0.378333",
                "DueDt": "", "RegMktCode": "10",
            }],
        },
        None, None,
    )
    assert result.block2_status == "not_provided"
    assert result.model_dump()["block2_status"] == "not_provided"
    assert result.block2.EvalPnlSum == placeholder
    assert "EvalPnl" not in result.block2.model_fields_set
    row = result.block3[0]
    assert (row.BalQty, row.BnsBaseBalQty, row.BuyUnsttQty) == (0, 1, 1)
    assert row.PchsAmt == 60000 and row.AvrUprc == 60000
    assert row.EvalPnl == 22700 and row.PnlRat == pytest.approx(0.378333)
    assert {"DueDt", "RegMktCode", "PchsAmt"} <= row.model_fields_set
    assert "Expdt" not in row.model_fields_set


def test_summary_status_cannot_be_overridden_as_available():
    with pytest.raises(ValidationError):
        CSPAQ12300Response(block2_status="available")


def test_example_consumes_real_fields_and_retains_missing_vs_observed_zero():
    example = load_example()
    assert set(example.POSITION_FIELDS) <= CSPAQ12300OutBlock3.model_fields.keys()
    absent = example.position_evidence(CSPAQ12300OutBlock3(IsuNo="A005930"))
    zero = example.position_evidence(CSPAQ12300OutBlock3(IsuNo="A005930", PchsAmt=0))
    assert absent["PchsAmt"] is None
    assert zero["PchsAmt"] == 0
    assert absent["AvrUprc"] is None and absent["PnlRat"] is None


def test_periodic_report_retains_example_record_count_and_source_echo_fields():
    request = FOCCQ33600InBlock1(QrySrtDt="20260908", QryEndDt="20260915", TermTp="1")
    assert request.model_dump()["RecCnt"] == 1
    echo = FOCCQ33600OutBlock1.model_validate({**request.model_dump(), "AcntNo": "fixture-account", "Pwd": "fixture-password"})
    assert {"RecCnt", "AcntNo", "Pwd", "QrySrtDt", "QryEndDt", "TermTp"} <= echo.model_fields_set
    assert "fixture-account" not in repr(echo)
    assert "fixture-password" not in repr(echo)
