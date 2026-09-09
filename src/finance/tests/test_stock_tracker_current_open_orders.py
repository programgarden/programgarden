"""The recurring stock pending-order query includes current-day activity."""
import asyncio
import socket
from types import SimpleNamespace

import pytest

from programgarden_finance.ls.overseas_stock.accno.COSAQ00102 import TrCOSAQ00102
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102.blocks import (
    COSAQ00102InBlock1, COSAQ00102OutBlock3, COSAQ00102Response,
)
from programgarden_finance.ls.overseas_stock.extension.tracker import StockAccountTracker


def test_tracker_includes_current_day_and_delivers_pending_row(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network transport is forbidden")

    for method in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, method, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    requests = []
    notices = []

    class API:
        def cosaq00102(self, body):
            requests.append(body)
            return self

        async def req_async(self):
            return COSAQ00102Response(
                rsp_cd="00000", rsp_msg="Synthetic success",
                block3=[COSAQ00102OutBlock3(
                    OrdNo=17, ShtnIsuNo="AAPL", OrdQty=1.25, ExecQty=0.25,
                    UnercQty=1, OvrsOrdPrc=100,
                )],
            )

    tracker = StockAccountTracker(API())
    tracker._on_open_orders_change_callbacks.append(lambda orders: notices.append(orders))
    asyncio.run(tracker._fetch_open_orders())
    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, COSAQ00102InBlock1)
    assert request.ThdayBnsAppYn == "1"
    assert request.ExecYn == "2"
    assert len(request.OrdDt) == 8 and request.OrdDt.isdigit()
    assert not tracker._last_errors
    assert notices and len(notices[-1]) == 1
    pending = next(iter(notices[-1].values()))
    assert pending.symbol == "AAPL"
    assert pending.order_qty == 1.25
    assert pending.executed_qty == 0.25
    assert pending.remaining_qty == 1


def _response(payload, status=200, headers=None):
    return TrCOSAQ00102._build_response(
        TrCOSAQ00102.__new__(TrCOSAQ00102),
        SimpleNamespace(status_code=status), payload, headers or {}, None,
    )


@pytest.mark.parametrize("failure", [
    None,
    _response({}),
    _response({"rsp_cd": "00000", "rsp_msg": "Synthetic missing blocks"}),
    _response({"rsp_cd": "00000", "rsp_msg": "Synthetic missing detail block",
               "COSAQ00102OutBlock1": {}, "COSAQ00102OutBlock2": {}}),
    _response({"rsp_cd": "02679", "rsp_msg": "조회내역이 없습니다.",
               "COSAQ00102OutBlock1": {"OrdMktCode": "81"},
               "COSAQ00102OutBlock2": {}, "COSAQ00102OutBlock3": []}),
    _response({"rsp_cd": "SYNTHETIC_UNKNOWN", "rsp_msg": "조회내역 unavailable"}),
    _response({"rsp_cd": "00000", "rsp_msg": "Synthetic HTTP failure"}, 503),
    _response({"rsp_cd": "00000", "rsp_msg": "Synthetic missing identity",
               "COSAQ00102OutBlock3": [{}]}),
])
def test_unusable_response_preserves_pending_orders_and_original_diagnostics(failure):
    class API:
        def cosaq00102(self, body):
            return self

        async def req_async(self):
            return failure

    tracker = StockAccountTracker(API())
    previous = object()
    tracker._open_orders = {"17": previous}
    notices = []
    tracker._on_open_orders_change_callbacks.append(notices.append)
    asyncio.run(tracker._fetch_open_orders())
    assert tracker._open_orders == {"17": previous}
    assert notices == []
    diagnostic = tracker._last_errors["open_orders"]
    assert "COSAQ00102" in diagnostic
    if failure is not None:
        assert f"rsp_cd={failure.rsp_cd}" in diagnostic
        assert f"rsp_msg={failure.rsp_msg}" in diagnostic
        assert f"error_msg={failure.error_msg}" in diagnostic


def test_complete_empty_success_removes_prior_pending_orders():
    class API:
        def cosaq00102(self, body):
            return self

        async def req_async(self):
            return _response({
                "rsp_cd": "00000", "rsp_msg": "Synthetic empty success",
                "COSAQ00102OutBlock1": {}, "COSAQ00102OutBlock2": {},
                "COSAQ00102OutBlock3": [],
            })

    tracker = StockAccountTracker(API())
    tracker._open_orders = {"17": object()}
    tracker._last_errors["open_orders"] = "Previous failure"
    notices = []
    tracker._on_open_orders_change_callbacks.append(notices.append)
    asyncio.run(tracker._fetch_open_orders())
    assert tracker._open_orders == {}
    assert notices == [{}]
    assert tracker._last_errors == {}


@pytest.mark.parametrize("variant, clears", [
    ("observed", True),
    ("missing_detail", False),
    ("missing_aggregate", False),
    ("other_market", False),
    ("other_date", False),
    ("continuation", False),
    ("missing_header", False),
    ("unexpected_rows", False),
    ("sell_only", False),
    ("other_currency", False),
    ("filled_only", False),
    ("object_detail", False),
    ("string_detail", False),
    ("null_detail", False),
])
def test_observed_no_data_response_is_scoped_to_complete_pending_query(variant, clears):
    class API:
        def cosaq00102(self, body):
            self.body = body
            return self

        async def req_async(self):
            payload = {
                "rsp_cd": "02679", "rsp_msg": "조회내역이 없습니다.",
                "COSAQ00102OutBlock1": {"OrdDt": self.body.OrdDt,
                    "OrdMktCode": "%", "ThdayBnsAppYn": "1",
                    "BnsTpCode": "0", "CrcyCode": "000"},
                "COSAQ00102OutBlock2": {"RecCnt": 1},
                "COSAQ00102OutBlock3": [],
            }
            headers = {"Content-Type": "application/json", "tr_cd": "COSAQ00102",
                       "tr_cont": "N", "tr_cont_key": ""}
            if variant == "missing_detail":
                del payload["COSAQ00102OutBlock3"]
            elif variant == "missing_aggregate":
                del payload["COSAQ00102OutBlock2"]
            elif variant == "other_market":
                payload["COSAQ00102OutBlock1"]["OrdMktCode"] = "81"
            elif variant == "other_date":
                payload["COSAQ00102OutBlock1"]["OrdDt"] = "19990101"
            elif variant == "continuation":
                headers.update(tr_cont="Y", tr_cont_key="synthetic-next")
            elif variant == "missing_header":
                headers = {}
            elif variant == "unexpected_rows":
                payload["COSAQ00102OutBlock3"] = [{"OrdNo": 17, "UnercQty": 1}]
            elif variant == "sell_only":
                payload["COSAQ00102OutBlock1"]["BnsTpCode"] = "1"
            elif variant == "other_currency":
                payload["COSAQ00102OutBlock1"]["CrcyCode"] = "JPY"
            elif variant == "filled_only":
                payload["COSAQ00102OutBlock1"]["ExecYn"] = "1"
            elif variant == "object_detail":
                payload["COSAQ00102OutBlock3"] = {}
            elif variant == "string_detail":
                payload["COSAQ00102OutBlock3"] = ""
            elif variant == "null_detail":
                payload["COSAQ00102OutBlock3"] = None
            return _response(payload, headers=headers)

    tracker = StockAccountTracker(API())
    previous = object()
    tracker._open_orders = {"17": previous}
    tracker._last_errors["open_orders"] = "Previous failure"
    notices = []
    tracker._on_open_orders_change_callbacks.append(notices.append)
    asyncio.run(tracker._fetch_open_orders())
    assert tracker._open_orders == ({} if clears else {"17": previous})
    assert notices == ([{}] if clears else [])
    assert ("open_orders" not in tracker._last_errors) is clears
