"""Current stock pending-order reads include same-day activity."""
import asyncio
import socket
from types import SimpleNamespace

from programgarden.executor import OpenOrdersNodeExecutor
from programgarden_finance.ls.overseas_stock.accno.COSAQ00102.blocks import (
    COSAQ00102InBlock1, COSAQ00102OutBlock3, COSAQ00102Response,
)


def test_open_orders_includes_current_day_and_preserves_fractional_row(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network transport is forbidden")

    for method in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, method, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    requests = []
    row = COSAQ00102OutBlock3(
        OrdNo=17, ShtnIsuNo="AAPL", BnsTpCode="02", OrdQty=1.25,
        ExecQty=0.25, UnercQty=1, OvrsOrdPrc=100,
    )

    class API:
        def overseas_stock(self):
            return self

        def accno(self):
            return self

        def cosaq00102(self, body):
            requests.append(body)
            return self

        async def req_async(self):
            return COSAQ00102Response(rsp_cd="00000", rsp_msg="Synthetic success", block3=[row])

    node = OpenOrdersNodeExecutor.__new__(OpenOrdersNodeExecutor)
    result = asyncio.run(node._ls_overseas_stock(
        API(), "synthetic-node", SimpleNamespace(log=lambda *args: None),
    ))
    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, COSAQ00102InBlock1)
    assert request.ThdayBnsAppYn == "1"
    assert request.ExecYn == "2"
    assert len(request.OrdDt) == 8 and request.OrdDt.isdigit()
    assert result["count"] == 1
    assert result["open_orders"][0]["quantity"] == 1.25
    assert result["open_orders"][0]["filled_quantity"] == 0.25
    assert result["open_orders"][0]["remaining_quantity"] == 1
