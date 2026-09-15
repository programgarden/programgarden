"""Broker equity and business-day cash flows retain their actual source evidence."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ03000 import (
    TrCIDBQ03000, blocks,
)
from programgarden_finance.ls.overseas_futureoption.extension.account_snapshot import (
    SNAPSHOT_FIELDS, futures_account_snapshot,
)
from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
REQUEST = blocks.CIDBQ03000InBlock1(RecCnt=1, AcntTpCode="1", TrdDt="")
HEADER = blocks.CIDBQ03000ResponseHeader(
    content_type="application/json", tr_cd="CIDBQ03000", tr_cont="N", tr_cont_key="",
).model_dump(by_alias=True)


def payload():
    return {
        "rsp_cd": "00136", "rsp_msg": "completed",
        "CIDBQ03000OutBlock1": {**REQUEST.model_dump(), "AcntNo": "PRIVATE_ACCOUNT", "AcntPwd": "PRIVATE_PASSWORD"},
        "CIDBQ03000OutBlock2": [
            {"AcntNo": "PRIVATE_ACCOUNT", "TrdDt": "", "CrcyObjCode": "HKD",
             "EvalAssetAmt": "998910.00", "CustmMnyioAmt": "0.00",
             "AbrdFutsEvalPnlAmt": "-890.00", "AbrdFutsCsgnMgn": "10000.00"},
            {"TrdDt": "", "CrcyObjCode": "USD", "EvalAssetAmt": "200.00",
             "CustmMnyioAmt": "100.00", "AbrdFutsEvalPnlAmt": "0.00"},
            {"TrdDt": "", "CrcyObjCode": "TOT(USD)", "EvalAssetAmt": "128264.10",
             "CustmMnyioAmt": "100.00", "AbrdFutsEvalPnlAmt": "-114.10"},
        ],
    }


def parse(data=None, header=None):
    return TrCIDBQ03000._build_response(
        None, SimpleNamespace(status=200), data if data is not None else payload(),
        HEADER if header is None else header, None,
    )


def test_consumed_field_contract_matches_actual_models():
    assert SNAPSHOT_FIELDS <= blocks.CIDBQ03000OutBlock2.model_fields.keys()
    assert {"RecCnt", "AcntTpCode", "TrdDt"} <= blocks.CIDBQ03000OutBlock1.model_fields.keys()
    assert {"RecCnt", "AcntTpCode", "TrdDt"} <= blocks.CIDBQ03000InBlock1.model_fields.keys()
    assert {"tr_cd", "tr_cont", "tr_cont_key"} <= blocks.CIDBQ03000ResponseHeader.model_fields.keys()


def test_native_and_aggregate_rows_are_distinct_without_double_counting_pnl():
    response = parse()
    before = response.model_dump()
    value = futures_account_snapshot(response, REQUEST, NOW)
    assert value["cash_flow_basis"] == "business_day_net"
    assert value["source"] == "CIDBQ03000"
    assert value["trading_date"] is None
    assert value["requested_date"] is None
    hkd, aggregate, usd = value["rows"]
    assert hkd["equity"] == Decimal("998910.00")
    assert hkd["unrealized_pnl"] == Decimal("-890.00")
    assert hkd["daily_net_cash_flow"] == 0
    assert aggregate["currency_target"] == "TOT(USD)"
    assert aggregate["aggregation"] == "broker_aggregate"
    assert usd["aggregation"] == "native_currency"
    assert "total" not in value and "return" not in value
    assert "PRIVATE" not in str(value)
    assert "PRIVATE" not in str(response._account_snapshot_rows)
    assert response.model_dump() == before


def test_wire_precision_is_preserved_before_float_conversion():
    data = payload()
    data["CIDBQ03000OutBlock2"][0]["EvalAssetAmt"] = "9007199254740993.12"
    value = futures_account_snapshot(parse(data), REQUEST, NOW)
    assert value["rows"][0]["equity"] == Decimal("9007199254740993.12")


def test_observed_paper_header_uses_family_code_with_exact_payload_blocks():
    # Captured paper CIDBQ03000 response on 2026-09-15 has tr_cd=CIDBQ.
    header = {**HEADER, "tr_cd": "CIDBQ"}
    assert futures_account_snapshot(parse(header=header), REQUEST, NOW) is not None
    data = payload()
    data["CIDBQ05300OutBlock2"] = data.pop("CIDBQ03000OutBlock2")
    assert futures_account_snapshot(parse(data, header=header), REQUEST, NOW) is None


@pytest.mark.parametrize("field", ["CustmMnyioAmt", "AbrdFutsEvalPnlAmt", "AbrdFutsCsgnMgn"])
def test_missing_optional_amount_stays_unknown(field):
    data = payload()
    data["CIDBQ03000OutBlock2"][0].pop(field)
    value = futures_account_snapshot(parse(data), REQUEST, NOW)
    output = {"CustmMnyioAmt": "daily_net_cash_flow", "AbrdFutsEvalPnlAmt": "unrealized_pnl", "AbrdFutsCsgnMgn": "margin"}[field]
    assert value["rows"][0][output] is None


@pytest.mark.parametrize("case", ["missing_equity", "missing_currency", "missing_date", "missing_rows", "empty_rows", "duplicate", "date_mismatch", "invalid_date", "currency", "boolean", "nan", "infinity", "unknown_code", "echo_missing", "echo_mismatch"])
def test_unsupported_or_partial_evidence_is_not_a_zero_snapshot(case):
    data = payload()
    rows = data["CIDBQ03000OutBlock2"]
    if case == "missing_equity": rows[0].pop("EvalAssetAmt")
    elif case == "missing_currency": rows[0].pop("CrcyObjCode")
    elif case == "missing_date": rows[0].pop("TrdDt")
    elif case == "missing_rows": data.pop("CIDBQ03000OutBlock2")
    elif case == "empty_rows": data["CIDBQ03000OutBlock2"] = []
    elif case == "duplicate": rows.append(deepcopy(rows[0]))
    elif case == "date_mismatch": rows[0]["TrdDt"] = "20260914"
    elif case == "invalid_date": rows[0]["TrdDt"] = "20260230"
    elif case == "currency": rows[0]["CrcyObjCode"] = "TOTAL"
    elif case == "boolean": rows[0]["CustmMnyioAmt"] = True
    elif case == "nan": rows[0]["CustmMnyioAmt"] = float("nan")
    elif case == "infinity": rows[0]["EvalAssetAmt"] = float("inf")
    elif case == "unknown_code": data["rsp_cd"] = "99999"
    elif case == "echo_missing": data["CIDBQ03000OutBlock1"].pop("TrdDt")
    elif case == "echo_mismatch": data["CIDBQ03000OutBlock1"]["AcntTpCode"] = "2"
    assert futures_account_snapshot(parse(data), REQUEST, NOW) is None


@pytest.mark.parametrize("case", ["http", "error", "missing_header", "wrong_tr", "continued", "continuation_key", "naive_time"])
def test_transport_and_continuation_contract(case):
    response = parse()
    now = NOW
    if case == "http": response.status_code = 500
    elif case == "error": response.error_msg = "request_failed"
    elif case == "missing_header": response.header = None
    elif case == "wrong_tr": response.header.tr_cd = "CIDBQ01500"
    elif case == "continued": response.header.tr_cont = "Y"
    elif case == "continuation_key": response.header.tr_cont_key = "next"
    elif case == "naive_time": now = now.replace(tzinfo=None)
    assert futures_account_snapshot(response, REQUEST, now) is None


def test_explicit_negative_equity_and_withdrawal_are_preserved():
    data = payload()
    data["CIDBQ03000OutBlock2"][0].update(EvalAssetAmt="-100.50", CustmMnyioAmt="-200.00")
    value = futures_account_snapshot(parse(data), REQUEST, NOW)
    assert value["rows"][0]["equity"] == Decimal("-100.50")
    assert value["rows"][0]["daily_net_cash_flow"] == Decimal("-200.00")


def test_observation_clock_cannot_invent_broker_business_day():
    first = futures_account_snapshot(parse(), REQUEST, NOW)
    next_day = futures_account_snapshot(parse(), REQUEST, NOW + timedelta(days=1))
    assert first["trading_date"] is next_day["trading_date"] is None
    assert first["rows"] == next_day["rows"]
    assert first["observed_at"] != next_day["observed_at"]


def test_explicit_query_dates_and_daily_reset_are_kept_as_source_observations():
    values = []
    for date, cash_flow in [("20260914", "500"), ("20260915", "0")]:
        request = blocks.CIDBQ03000InBlock1(RecCnt=1, AcntTpCode="1", TrdDt=date)
        data = payload()
        data["CIDBQ03000OutBlock1"]["TrdDt"] = date
        for row in data["CIDBQ03000OutBlock2"]:
            row.update(TrdDt=date, CustmMnyioAmt=cash_flow)
        values.append(futures_account_snapshot(parse(data), request, NOW))
    assert values[0]["rows"][0]["daily_net_cash_flow"] == 500
    assert values[1]["rows"][0]["daily_net_cash_flow"] == 0
    assert values[1]["trading_date"] == "20260915"


@pytest.mark.asyncio
async def test_tracker_reuses_one_existing_query_and_returns_immutable_snapshot():
    client = MagicMock()
    client.CIDBQ03000.return_value.req_async = AsyncMock(return_value=parse())
    tracker = FuturesAccountTracker(client, MagicMock())
    for _ in range(2):
        await tracker._fetch_balance()
        value = tracker.get_account_snapshot()
        assert value["rows"][2]["daily_net_cash_flow"] == 100
        value["rows"][2]["daily_net_cash_flow"] = 900
        assert tracker.get_account_snapshot()["rows"][2]["daily_net_cash_flow"] == 100
    assert client.CIDBQ03000.call_count == 2
    assert client.CIDBQ03000.call_args.kwargs["body"] == REQUEST
    client.CIDBQ05300.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["transport", "missing", "rejection"])
async def test_latest_failed_refresh_clears_supported_snapshot(failure):
    client = MagicMock()
    query = client.CIDBQ03000.return_value
    query.req_async = AsyncMock(return_value=parse())
    tracker = FuturesAccountTracker(client, MagicMock())
    await tracker._fetch_balance()
    assert tracker.get_account_snapshot() is not None
    if failure == "transport":
        query.req_async.side_effect = RuntimeError("offline")
    else:
        data = payload()
        data.pop("CIDBQ03000OutBlock2")
        if failure == "rejection": data.update(rsp_cd="99999", rsp_msg="rejected")
        query.req_async.return_value = parse(data)
    await tracker._fetch_balance()
    assert tracker.get_account_snapshot() is None
