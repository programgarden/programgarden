"""Classify real SDK empty envelopes without issuing broker requests."""

import asyncio
import socket
from types import SimpleNamespace

import pytest

from programgarden.executor import OpenOrdersNodeExecutor
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102 import TrCOSAQ00102
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102.blocks import (
    COSAQ00102OutBlock1,
    COSAQ00102OutBlock3,
    COSAQ00102Response,
    COSAQ00102ResponseHeader,
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network transport is forbidden")

    for method in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, method, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def read_orders(variant="observed", code="02679"):
    requests, logs = [], []

    class API:
        def overseas_stock(self):
            return self

        def accno(self):
            return self

        def cosaq00102(self, body):
            requests.append(body)
            self.body = body
            return self

        async def req_async(self):
            echo = self.body.model_dump()
            echo["OrdMktCode"] = "%"
            payload = {
                "rsp_cd": code, "rsp_msg": "Synthetic broker response",
                "COSAQ00102OutBlock1": echo,
                "COSAQ00102OutBlock2": {"RecCnt": 1},
                "COSAQ00102OutBlock3": [],
            }
            headers = {"Content-Type": "application/json", "tr_cd": "COSAQ00102",
                       "tr_cont": "N", "tr_cont_key": ""}
            status = 200
            if variant == "omitted_optional_echo":
                for key in ("QryTpCode", "BkseqTpCode", "IsuNo", "SrtOrdNo", "ExecYn", "LoanBalHldYn"):
                    echo.pop(key)
            elif variant.startswith("missing_"):
                key = {"missing_detail": "COSAQ00102OutBlock3",
                       "missing_echo": "COSAQ00102OutBlock1",
                       "missing_aggregate": "COSAQ00102OutBlock2"}.get(variant)
                if key:
                    payload.pop(key)
                elif variant == "missing_header":
                    headers = {}
            elif variant.startswith("echo_"):
                key = variant.removeprefix("echo_")
                echo[key] = 0 if key == "SrtOrdNo" else "synthetic-mismatch"
            elif variant == "continuation":
                headers.update(tr_cont="Y", tr_cont_key="synthetic-next")
            elif variant == "continuation_key":
                headers["tr_cont_key"] = "synthetic-next"
            elif variant in ("object_detail", "string_detail", "null_detail"):
                payload["COSAQ00102OutBlock3"] = {
                    "object_detail": {}, "string_detail": "", "null_detail": None,
                }[variant]
            elif variant == "unexpected_rows":
                payload["COSAQ00102OutBlock3"] = [{"OrdNo": 17, "UnercQty": 1}]
            elif variant == "http_failure":
                status = 503
            elif variant == "exception":
                raise TimeoutError("Synthetic request timeout")
            elif variant == "no_response":
                return None
            return TrCOSAQ00102._build_response(
                TrCOSAQ00102.__new__(TrCOSAQ00102),
                SimpleNamespace(status_code=status), payload, headers, None,
            )

    result = asyncio.run(OpenOrdersNodeExecutor()._ls_overseas_stock(
        API(), "synthetic-node", SimpleNamespace(log=lambda *args: logs.append(args)),
    ))
    assert len(requests) == 1
    return result, logs


@pytest.mark.parametrize("code,variant", [
    ("02679", "observed"), ("02679", "omitted_optional_echo"), ("00000", "observed"),
])
def test_complete_empty_response_is_zero_orders_without_error(code, variant):
    result, logs = read_orders(variant, code)
    assert result == {"open_orders": [], "count": 0}
    assert not any(log[0] in ("error", "warning") for log in logs)


@pytest.mark.parametrize("variant", [
    "missing_detail", "missing_echo", "missing_aggregate", "missing_header",
    "continuation", "continuation_key", "unexpected_rows",
    "object_detail", "string_detail", "null_detail", "http_failure", "exception", "no_response",
    *(f"echo_{key}" for key in ("OrdDt", "OrdMktCode", "ThdayBnsAppYn", "BnsTpCode",
       "CrcyCode", "QryTpCode", "BkseqTpCode", "IsuNo", "SrtOrdNo", "ExecYn", "LoanBalHldYn")),
])
def test_incomplete_or_mismatched_no_data_response_remains_a_query_failure(variant):
    result, logs = read_orders(variant)
    assert result["error"]
    assert result["reason"] == "fetch_failed"
    assert result["diagnostics"]["tr"] == "COSAQ00102"
    if variant not in ("exception", "no_response"):
        assert result["diagnostics"]["rsp_cd"] == "02679"
        assert "exception_type" not in result["diagnostics"]
    assert any(log[0] == "error" for log in logs)


@pytest.mark.parametrize("code,variant", [
    ("00000", "missing_detail"), ("00000", "missing_echo"), ("00000", "missing_aggregate"),
    ("SYNTHETIC_UNKNOWN", "observed"),
])
def test_other_responses_cannot_silently_clear_pending_buy_guards(code, variant):
    result, _ = read_orders(variant, code)
    assert result["error"]
    assert result["diagnostics"]["rsp_cd"] == code


@pytest.mark.parametrize("model,fields", [
    (COSAQ00102Response, "status_code rsp_cd rsp_msg error_msg block1 block2 block3 header"),
    (COSAQ00102ResponseHeader, "tr_cont tr_cont_key"),
    (COSAQ00102OutBlock1, "OrdDt OrdMktCode ThdayBnsAppYn BnsTpCode CrcyCode QryTpCode BkseqTpCode IsuNo SrtOrdNo ExecYn LoanBalHldYn"),
    (COSAQ00102OutBlock3, "OrdNo BnsTpCode OrdMktCode ShtnIsuNo IsuNo JpnMktHanglIsuNm OrdQty ExecQty UnercQty OvrsOrdPrc OrdTime"),
])
def test_consumed_fields_exist_in_the_actual_sdk_models(model, fields):
    assert set(fields.split()) <= model.model_fields.keys()
