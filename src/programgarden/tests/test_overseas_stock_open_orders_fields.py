"""해외주식 미체결 주문 dict 의 필드 출처 — 없는 값을 사실처럼 내보내지 않는다.

``exchange`` 가 비는 원인은 **브로커가 아니라 SDK 매핑**이다. 브로커 응답
COSAQ00102OutBlock3 에는 주문시장코드가 있다(SDK overseas_stock/accno/
COSAQ00102/blocks.py:534 ``OrdMktCode`` — "'81' = NYSE, '82' = NASDAQ").
그 행을 ``StockOpenOrder`` 로 옮기는 매핑(overseas_stock/extension/
tracker.py:385-398)이 그 필드를 읽지 않고, 모델에도 자리가 없다
(extension/models.py:189-226). 그래서 사유는 "브로커가 안 줌" 이 아니라
"중간 매핑에서 유실" 이어야 한다. 키는 포트 스키마(ORDER_LIST_FIELDS 에
exchange 선언)와 형제 경로(선물/국내) 모양을 위해 남기되, 사유를 같은 dict 에
실어 소비자가 오해하지 않게 한다. 근본 수정(SDK 모델에 market_code 추가)은
finance 패키지 몫이라 여기 범위 밖이다.

수량 필드는 int 로 자르지 않는다 — LS 해외주식은 소수점 거래를 지원하고
(출처: 오너 진술 2026-09-12; prod 2026-08-24 IBM 0.847972주 실측),
``int()`` 로 자르면 1주 미만 미체결이 통째로 0 이 돼 조용히 사라진다.
체결수량 필드명도 ``filled_qty`` 가 아니라 ``executed_qty`` 다(models.py:210).
"""

from types import SimpleNamespace

from programgarden.executor import RealAccountNodeExecutor


class _Tracker:
    def __init__(self, orders):
        self._orders = orders

    def get_open_orders(self):
        return self._orders

    def get_positions(self):
        return {}

    def get_balances(self):
        return {}


def _open_orders(order):
    data = RealAccountNodeExecutor()._get_overseas_stock_tracker_data(_Tracker({"A1": order}))
    return data["open_orders"]["A1"]


def test_exchange_is_marked_unavailable_not_silently_empty():
    """사유 문자열은 실제 원인(= SDK 매핑 유실)을 말해야 한다.

    종전 값 "not_provided_by_broker_open_order" 는 사실이 아니었다 — 브로커는
    OrdMktCode 를 준다(COSAQ00102/blocks.py:534).
    """
    row = _open_orders(SimpleNamespace(
        symbol="IBM", order_type="02", order_price=250.0,
        order_qty=1, executed_qty=0, remaining_qty=1,
    ))

    assert row["exchange"] == ""
    assert row["exchange_unavailable_reason"] == "dropped_by_sdk_open_order_mapping"


def test_fractional_quantities_survive_and_executed_qty_is_read():
    row = _open_orders(SimpleNamespace(
        symbol="IBM", order_type="02", order_price=250.0,
        order_qty=0.847972, executed_qty=0.5, remaining_qty=0.347972,
    ))

    assert row["order_qty"] == 0.847972
    assert row["filled_qty"] == 0.5       # executed_qty 를 읽어야 한다 (filled_qty 아님)
    assert row["remaining_qty"] == 0.347972


def test_integer_quantities_stay_integers():
    row = _open_orders(SimpleNamespace(
        symbol="IBM", order_type="02", order_price=250.0,
        order_qty=3, executed_qty=1, remaining_qty=2,
    ))

    assert (row["order_qty"], row["filled_qty"], row["remaining_qty"]) == (3, 1, 2)
    assert all(isinstance(row[k], int) for k in ("order_qty", "filled_qty", "remaining_qty"))


def test_exchange_reason_is_absent_when_the_broker_does_report_one():
    """SDK 모델이 거래소를 싣게 되면 사유 없이 실제 값이 나가야 한다."""
    row = _open_orders(SimpleNamespace(
        symbol="IBM", order_type="02", order_price=250.0,
        order_qty=1, executed_qty=0, remaining_qty=1,
        exchange_code="NASDAQ",
    ))

    assert row["exchange"] == "NASDAQ"
    assert "exchange_unavailable_reason" not in row
