"""Schema/presence fixtures, not live evidence of broker deposit coverage."""

from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from programgarden_finance import CDPCQ04700
from programgarden_finance.ls.korea_stock.accno.CDPCQ04700 import blocks


def parse(payload):
    request = CDPCQ04700.CDPCQ04700Request(body={
        "CDPCQ04700InBlock1": CDPCQ04700.CDPCQ04700InBlock1(
            QryTp="1", QrySrtDt="20260921", QryEndDt="20260921",
            PdptnCode="01", IsuLgclssCode="00", IsuNo="", SrtNo=0,
        ),
    })
    tr = CDPCQ04700.TrCDPCQ04700(request)
    return tr._build_response(SimpleNamespace(status_code=200), payload, {}, None)


def test_all_current_official_response_fields_are_modeled():
    contract = json.loads((Path(__file__).parent / "fixtures/cdpcq04700_official_fields.json").read_text())
    assert sum(len(fields) for fields in contract["response"].values()) == 111
    for name, fields in contract["response"].items():
        model = getattr(blocks, name)
        assert set(fields) <= set(model.model_fields), name


def test_foreign_cash_fields_and_summary_blocks_survive_parsing():
    payload = {"rsp_cd": "00000", "rsp_msg": "fixture", "CDPCQ04700OutBlock3": [{
        "TrdDt": "20260921", "TrdNo": 7, "CrcyCode": "USD", "FcurrAdjstAmt": "1.2500",
        "FcurrDpsBfbalAmt": "500.0000", "DpsBfbalAmt": 0,
    }], "CDPCQ04700OutBlock4": {"PnlSumAmt": 0},
        "CDPCQ04700OutBlock5": {"MnyinAmt": 1000, "MnyoutAmt": 0}}
    response = parse(payload)
    assert response.error_msg is None
    assert response.block3[0].FcurrAdjstAmt == Decimal("1.2500")
    assert response.block3[0].CrcyCode == "USD"
    assert response.block4.PnlSumAmt == 0
    assert response.block5.MnyinAmt == 1000 and response.block5.MnyoutAmt == 0
    assert response.raw_payload == payload


@pytest.mark.parametrize("value", [None, "", 0, "0"])
def test_present_blank_null_zero_remain_distinguishable_from_missing(value):
    response = parse({"CDPCQ04700OutBlock3": [{"DpsBfbalAmt": value, "AdjstAmt": value}],
                      "CDPCQ04700OutBlock5": {"MnyinAmt": value}})
    assert response.error_msg is None
    row = response.block3[0]
    assert {"DpsBfbalAmt", "AdjstAmt"} <= row.model_fields_set
    assert "MnyoutAmt" not in response.block5.model_fields_set
    assert response.raw_payload["CDPCQ04700OutBlock5"]["MnyinAmt"] == value
    assert row.DpsBfbalAmt == (0 if value == "0" else value)


def test_legacy_defaults_do_not_claim_broker_presence():
    response = parse({"CDPCQ04700OutBlock3": [{}]})
    row = response.block3[0]
    assert row.AdjstAmt == 0 and "AdjstAmt" not in row.model_fields_set
    assert row.DpsBfbalAmt is None and "DpsBfbalAmt" not in row.model_fields_set
    assert row.model_dump(exclude_unset=True) == {}


def test_missing_detail_is_not_explicit_empty_and_raw_is_private_copy():
    missing = parse({"rsp_cd": "00000"})
    empty = parse({"CDPCQ04700OutBlock3": [], "unexpected_block": {"field": "kept"}})
    assert missing.block3 == empty.block3 == []
    assert "block3" not in missing.model_fields_set and "block3" in empty.model_fields_set
    assert "_raw_payload" not in empty.model_dump() and "raw_payload" not in empty.model_dump()
    copy = empty.raw_payload
    copy["unexpected_block"]["field"] = "changed"
    assert empty.raw_payload["unexpected_block"]["field"] == "kept"


@pytest.mark.parametrize("bad", [None, {}, "", ["invalid-row"]])
def test_malformed_detail_is_an_error_not_empty_success(bad):
    response = parse({"rsp_cd": "00000", "CDPCQ04700OutBlock3": bad})
    assert response.error_msg == "Malformed CDPCQ04700OutBlock3 response"
    assert response.raw_payload["CDPCQ04700OutBlock3"] == bad


def test_unknown_fields_are_retained_without_claiming_financial_meaning():
    response = parse({"CDPCQ04700OutBlock3": [{"NewBrokerField": "123"}]})
    assert response.block3[0].model_dump(exclude_unset=True) == {"NewBrokerField": "123"}


def test_malformed_header_keeps_raw_response_and_error_logs_exclude_account_data(caplog):
    request = CDPCQ04700.CDPCQ04700Request(body={
        "CDPCQ04700InBlock1": CDPCQ04700.CDPCQ04700InBlock1()})
    tr = CDPCQ04700.TrCDPCQ04700(request)
    raw = {"rsp_msg": "private account fixture", "CDPCQ04700OutBlock3": []}
    bad_header = tr._build_response(SimpleNamespace(status_code=200), raw,
                                    {"tr_cont": "invalid"}, None)
    assert bad_header.raw_payload == raw
    assert bad_header.error_msg == "Malformed CDPCQ04700 response header"
    failed = tr._build_response(SimpleNamespace(status_code=500), raw, {}, None)
    assert failed.rsp_msg == "private account fixture" and failed.error_msg == "HTTP 500"
    assert failed.raw_payload == raw
    tr._build_response(None, None, None, ValueError("private account fixture"))
    assert "private account fixture" not in caplog.text
