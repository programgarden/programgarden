"""Stock read failures retain original responses without fabricating empty success."""
import asyncio
import socket
from types import SimpleNamespace

import pytest

import programgarden.executor as ex
from programgarden_core.expression import ExpressionContext
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102 import TrCOSAQ00102
from programgarden_finance.ls.overseas_stock.market.g3101 import TrG3101


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network is forbidden in stock read regression tests")

    for method in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, method, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


class Context:
    is_deep_validate = False
    _iteration_item = None

    def __init__(self):
        self.logs = []

    def get_credential(self):
        return {"appkey": "synthetic-unused", "appsecret": "synthetic-unused", "paper_trading": False}

    def get_expression_context(self):
        return ExpressionContext()

    def get_output(self, *args):
        return None

    def log(self, level, message, node_id=None, **kwargs):
        self.logs.append((level, message))


def response(tr, payload, status=200, exception=None):
    cls = TrG3101 if tr == "g3101" else TrCOSAQ00102
    return cls._build_response(cls.__new__(cls), SimpleNamespace(status_code=status), payload, {}, exception)


class API:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def overseas_stock(self):
        return self

    def market(self):
        return self

    def accno(self):
        return self

    def g3101(self, body):
        self.requests.append(body)
        return self

    def cosaq00102(self, body):
        self.requests.append(body)
        return self

    def req(self):
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value

    async def req_async(self):
        return self.req()


def quote(monkeypatch, responses, symbols=None, public=False):
    api = API(responses)
    monkeypatch.setattr(ex, "ensure_ls_login", lambda *args, **kwargs: (api, True, None))
    node = ex.MarketDataNodeExecutor.__new__(ex.MarketDataNodeExecutor)
    symbols = symbols or [{"symbol": "AAPL", "exchange": "NASDAQ"}]
    if public:
        result = asyncio.run(node.execute("quote", "OverseasStockMarketDataNode", {
            "connection": {"product": "overseas_stock"}, "symbols": symbols,
        }, Context()))
    else:
        result = asyncio.run(node._fetch_overseas_stock(symbols, Context(), "quote"))
    return result, api


def valid_quote():
    return response("g3101", {
        "rsp_cd": "00000", "rsp_msg": "Synthetic success",
        "g3101OutBlock": {"symbol": "AAPL", "price": "100", "diff": "2", "sign": "5"},
    })


@pytest.mark.parametrize("failure", [
    None,
    response("g3101", {"rsp_cd": "SYNTHETIC_HTTP", "rsp_msg": "Synthetic unavailable"}, 503),
    response("g3101", {"rsp_cd": "SYNTHETIC_REJECT", "rsp_msg": "Synthetic rejection"}),
    response("g3101", {"rsp_cd": "00000", "rsp_msg": "Synthetic no snapshot"}),
])
def test_required_quote_failure_is_structured(monkeypatch, failure):
    result, api = quote(monkeypatch, [failure, failure], public=True)
    assert result["values"] == []
    assert result["error"] and result["reason"] == "fetch_failed"
    assert ex.NewOrderNodeExecutor._extract_upstream_error(result)
    assert len(api.requests) == 2
    attempts = result["failures"][0]["attempts"]
    assert len(attempts) == 2
    assert [item["exchange_code"] for item in attempts] == ["82", "81"]
    if failure is not None:
        assert attempts[0]["rsp_cd"] == failure.rsp_cd
        assert attempts[0]["rsp_msg"] == failure.rsp_msg
        assert attempts[0]["error_msg"] == failure.error_msg


def test_quote_attempts_preserve_distinct_original_messages(monkeypatch):
    failures = [response("g3101", {"rsp_cd": f"SYNTHETIC_{i}", "rsp_msg": f"Original {i}"}) for i in (1, 2)]
    result, _ = quote(monkeypatch, failures)
    assert [item["rsp_msg"] for item in result["failures"][0]["attempts"]] == ["Original 1", "Original 2"]


def test_quote_alternate_exchange_still_works(monkeypatch):
    empty = response("g3101", {"rsp_cd": "00000", "rsp_msg": "Synthetic no snapshot"})
    result, api = quote(monkeypatch, [empty, valid_quote()])
    assert len(api.requests) == 2
    assert result["values"][0]["price"] == 100
    assert result["values"][0]["exchange"] == "NYSE"
    assert result["values"][0]["change"] == -2
    assert not result.get("error") and not result.get("_partial_failure")


def test_quote_partial_success_keeps_values_and_failed_symbol(monkeypatch):
    failure = response("g3101", {"rsp_cd": "SYNTHETIC_REJECT", "rsp_msg": "Original failure"})
    result, api = quote(monkeypatch, [valid_quote(), failure, failure], [
        {"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"},
    ])
    assert len(api.requests) == 3
    assert [row["symbol"] for row in result["values"]] == ["AAPL"]
    assert result["_partial_failure"] is True
    assert result["_failure_reason"]
    assert result["failures"][0]["symbol"] == "MSFT"
    assert result["failures"][0]["attempts"][0]["rsp_msg"] == "Original failure"


def pending(responses, public=False, monkeypatch=None):
    api = API(responses)
    node = ex.OpenOrdersNodeExecutor.__new__(ex.OpenOrdersNodeExecutor)
    if public:
        monkeypatch.setattr(ex, "ensure_ls_login", lambda *args, **kwargs: (api, True, None))
        result = asyncio.run(node.execute("pending", "OverseasStockOpenOrdersNode", {
            "connection": {"product": "overseas_stock"},
        }, Context()))
    else:
        result = asyncio.run(node._ls_overseas_stock(api, "pending", Context()))
    return result, api


@pytest.mark.parametrize("failure", [
    None,
    response("COSAQ00102", {}),
    response("COSAQ00102", {"rsp_cd": "00000", "rsp_msg": "Blockless success code is insufficient"}),
    response("COSAQ00102", {"rsp_cd": "SYNTHETIC_REJECT", "rsp_msg": "Synthetic rejection"}),
    response("COSAQ00102", {"rsp_cd": "SYNTHETIC_HTTP", "rsp_msg": "Synthetic HTTP failure"}, 503),
    response("COSAQ00102", {"rsp_cd": "SYNTHETIC_REJECT", "rsp_msg": "Echo is not data", "COSAQ00102OutBlock1": {}}),
    response("COSAQ00102", {
        "rsp_cd": "SYNTHETIC_UNKNOWN", "rsp_msg": "Unknown even with envelope",
        "COSAQ00102OutBlock1": {}, "COSAQ00102OutBlock2": {}, "COSAQ00102OutBlock3": [],
    }),
])
def test_pending_unavailable_does_not_become_empty_success(monkeypatch, failure):
    result, api = pending([failure], public=True, monkeypatch=monkeypatch)
    assert result["error"] and result["reason"] == "fetch_failed"
    assert result["diagnostics"]["tr"] == "COSAQ00102"
    assert len(api.requests) == 1 and api.requests[0].ThdayBnsAppYn == "1"
    if failure is not None:
        assert result["diagnostics"]["rsp_cd"] == failure.rsp_cd
        assert result["diagnostics"]["rsp_msg"] == failure.rsp_msg
        assert result["diagnostics"]["error_msg"] == failure.error_msg


def test_pending_documented_success_empty_is_preserved():
    empty = response("COSAQ00102", {
        "rsp_cd": "00000", "rsp_msg": "Synthetic success",
        "COSAQ00102OutBlock1": {}, "COSAQ00102OutBlock2": {}, "COSAQ00102OutBlock3": [],
    })
    result, _ = pending([empty])
    assert result == {"open_orders": [], "count": 0}


def test_pending_nonempty_fractional_row_is_preserved():
    rows = response("COSAQ00102", {
        "rsp_cd": "00000", "rsp_msg": "Synthetic success", "COSAQ00102OutBlock3": [
            {"OrdNo": 17, "ShtnIsuNo": "AAPL", "BnsTpCode": "02", "OrdQty": 1.25, "ExecQty": 0.25, "UnercQty": 1},
        ],
    })
    result, _ = pending([rows])
    assert result["count"] == 1 and not result.get("error")
    assert result["open_orders"][0]["quantity"] == 1.25
    assert result["open_orders"][0]["filled_quantity"] == 0.25


def test_pending_transport_exception_keeps_original_message(monkeypatch):
    result, _ = pending([RuntimeError("Synthetic original transport error")], public=True, monkeypatch=monkeypatch)
    assert result["reason"] == "fetch_failed"
    assert result["diagnostics"]["tr"] == "COSAQ00102"
    assert result["diagnostics"]["error_msg"] == "Synthetic original transport error"


def test_quote_transport_exception_keeps_original_message(monkeypatch):
    result, _ = quote(monkeypatch, [RuntimeError("Synthetic original transport error")] * 2)
    assert result["reason"] == "fetch_failed"
    assert result["failures"][0]["attempts"][0]["error_msg"] == "Synthetic original transport error"


def test_unknown_code_with_usable_pending_row_keeps_existing_data_behavior():
    data = response("COSAQ00102", {
        "rsp_cd": "SYNTHETIC_UNKNOWN", "rsp_msg": "Synthetic usable data",
        "COSAQ00102OutBlock3": [{"OrdNo": 17, "ShtnIsuNo": "AAPL", "UnercQty": 1}],
    })
    result, _ = pending([data])
    assert result["count"] == 1 and not result.get("error")


def test_unusable_pending_identity_is_not_empty_evidence():
    data = response("COSAQ00102", {
        "rsp_cd": "00000", "rsp_msg": "Synthetic malformed identity",
        "COSAQ00102OutBlock1": {}, "COSAQ00102OutBlock2": {},
        "COSAQ00102OutBlock3": [{"OrdNo": 0}],
    })
    result, _ = pending([data])
    assert result["reason"] == "fetch_failed"
