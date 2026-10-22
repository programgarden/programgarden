"""Canonical local execution evidence uses supplied broker fields, offline."""

from datetime import date, datetime
from decimal import Decimal
import socket
from types import SimpleNamespace

import pytest

from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ02400.blocks import CIDBQ02400OutBlock2
from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ02400 import TrCIDBQ02400
from programgarden_finance.ls.overseas_futureoption.extension.execution_history import parse_futures_execution_history


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Execution parsing tests must remain offline")

    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)


def row(**changes):
    return dict(
        OrdDt="20260909", OvrsFutsOrdNo="0000000123",
        ExecDt="20260909", OvrsFutsExecNo="0000000456",
        ExecDttm="20260910001500123", OvrsDrvtExecIsuCode="SYNTHETIC",
        ExecBnsTpCode="2", ExecQty=1, AbrdFutsExecPrc="100.25",
        FutsOrdStatCode="1", TrxStatCodeNm="체결", TrdTpNm="매수", MdaCode="41",
    ) | changes


def test_actual_model_preserves_independent_dates_id_and_milliseconds():
    result = parse_futures_execution_history([CIDBQ02400OutBlock2(**row())])
    assert not result.issues
    execution, = result.executions
    assert execution.broker_order_no == "123" and execution.broker_execution_no == "456"
    assert execution.broker_order_date == date(2026, 9, 9)
    assert execution.broker_execution_date == date(2026, 9, 9)
    assert execution.execution_wall_time == datetime(2026, 9, 10, 0, 15, 0, 123000)
    assert execution.execution_wall_time.tzinfo is None
    assert execution.execution_datetime_raw == "20260910001500123"
    assert execution.quantity == Decimal("1") and execution.price == Decimal("100.25")
    assert execution.source_tr == "CIDBQ02400" and execution.source_status == "1"


def test_actual_sdk_response_builder_preserves_presence_before_canonical_parser():
    missing_price = row()
    missing_price.pop("AbrdFutsExecPrc")
    response = TrCIDBQ02400._build_response(None, SimpleNamespace(status=200), {
        "rsp_cd": "00136", "rsp_msg": "Synthetic fixture",
        "CIDBQ02400OutBlock2": [row(), missing_price],
    }, {}, None)
    result = parse_futures_execution_history(response.block2)
    assert len(result.executions) == 1
    assert result.executions[0].execution_wall_time.microsecond == 123000
    assert result.issues[0].reason == "missing_or_invalid_execution_price"


def test_opaque_broker_identifier_case_is_preserved_without_exchange_fallback():
    result = parse_futures_execution_history([row(OvrsFutsExecNo=" LS-AbC ", FcmOrdNo="999")])
    assert result.executions[0].broker_execution_no == "LS-AbC"
    result = parse_futures_execution_history([row(OvrsFutsExecNo="", FcmOrdNo="999")])
    assert not result.executions
    assert result.issues[0].reason == "missing_or_invalid_broker_execution_number"


@pytest.mark.parametrize("status", ["1", "4", "2", ""])
@pytest.mark.parametrize("side,expected", [("1", "sell"), ("2", "buy")])
def test_side_is_explicit_and_status_is_preserved_without_universal_filter(status, side, expected):
    result = parse_futures_execution_history([row(FutsOrdStatCode=status, ExecBnsTpCode=side)])
    assert not result.issues
    assert result.executions[0].side == expected
    assert result.executions[0].source_status == status


@pytest.mark.parametrize("quantity", [0, 1])
def test_cancellation_is_an_issue_without_deleting_or_netting_execution(quantity):
    result = parse_futures_execution_history([row(), row(ExecQty=quantity, TrxStatCodeNm="체결취소")])
    assert len(result.executions) == 1
    assert len(result.issues) == 1
    assert result.issues[0].reason == "execution_cancellation_effect_unverified"
    assert result.issues[0].broker_order_no == "123"
    assert result.issues[0].evidence["TrxStatCodeNm"] == "체결취소"


@pytest.mark.parametrize("field,reason", [
    ("OrdDt", "missing_or_invalid_broker_order_identity"),
    ("OvrsFutsOrdNo", "missing_or_invalid_broker_order_identity"),
    ("OvrsFutsExecNo", "missing_or_invalid_broker_execution_number"),
    ("ExecDt", "missing_or_invalid_broker_execution_date"),
    ("ExecDttm", "missing_or_invalid_execution_datetime"),
    ("ExecBnsTpCode", "missing_or_invalid_execution_side"),
    ("OvrsDrvtExecIsuCode", "missing_execution_symbol"),
    ("AbrdFutsExecPrc", "missing_or_invalid_execution_price"),
    ("ExecQty", "missing_or_invalid_execution_quantity"),
])
def test_response_model_defaults_cannot_supply_missing_execution_facts(field, reason):
    values = row()
    values.pop(field)
    result = parse_futures_execution_history([CIDBQ02400OutBlock2(**values)])
    assert not result.executions
    assert result.issues[0].reason == reason


@pytest.mark.parametrize("field,value,reason", [
    ("ExecBnsTpCode", "9", "missing_or_invalid_execution_side"),
    ("ExecQty", -1, "missing_or_invalid_execution_quantity"),
    ("ExecQty", "0.5", "missing_or_invalid_execution_quantity"),
    ("ExecQty", "NaN", "missing_or_invalid_execution_quantity"),
    ("ExecQty", True, "missing_or_invalid_execution_quantity"),
    ("AbrdFutsExecPrc", "Infinity", "missing_or_invalid_execution_price"),
    ("OvrsFutsExecNo", "0000", "missing_or_invalid_broker_execution_number"),
    ("OvrsFutsExecNo", "123.0", "missing_or_invalid_broker_execution_number"),
    ("ExecDt", "20260230", "missing_or_invalid_broker_execution_date"),
    ("ExecDttm", "20260910001500", "missing_or_invalid_execution_datetime"),
    ("ExecDttm", "20260910001500123456", "missing_or_invalid_execution_datetime"),
    ("ExecDttm", "20260910251500123", "missing_or_invalid_execution_datetime"),
    ("TrxStatCodeNm", "UNKNOWN", "execution_transaction_label_unverified"),
])
def test_invalid_evidence_stays_issue(field, value, reason):
    result = parse_futures_execution_history([row(**{field: value})])
    assert not result.executions and result.issues[0].reason == reason


@pytest.mark.parametrize("price", ["0", "-37.63", "100.2500"])
def test_explicit_zero_negative_and_decimal_quote_are_retained(price):
    result = parse_futures_execution_history([row(AbrdFutsExecPrc=price)])
    assert not result.issues and result.executions[0].price == Decimal(price)


def test_unfilled_is_not_execution_and_arbitrary_payload_is_not_retained():
    result = parse_futures_execution_history([
        row(ExecQty=0, FutsOrdStatCode="2"),
        row(AcntNo="SYNTHETIC_PRIVATE", Pwd="SYNTHETIC_PRIVATE", RegUserId="SYNTHETIC_PRIVATE"),
    ])
    assert len(result.executions) == 1 and not result.issues
    assert not any(key in result.executions[0].evidence for key in ("AcntNo", "Pwd", "RegUserId"))


def test_parser_does_not_invent_or_collapse_identity_for_partial_fill_arrivals():
    result = parse_futures_execution_history([row(), row(OvrsFutsExecNo="457"), row()])
    assert [event.broker_execution_no for event in result.executions] == ["456", "457", "456"]
    # Durable source-scoped idempotency is the store's responsibility.
    assert not result.issues
