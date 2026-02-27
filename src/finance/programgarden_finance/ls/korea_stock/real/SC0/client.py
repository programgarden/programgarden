"""주식주문접수(SC0) 실시간 클라이언트

EN:
    Client class for receiving real-time stock order acceptance notifications
    via WebSocket. Unlike market data TRs, order TRs (SC0-SC4) require account
    registration instead of symbol subscription. Registering SC0 automatically
    enables all five order event types (SC0/SC1/SC2/SC3/SC4).

KO:
    주식주문접수(SC0) 실시간 알림을 WebSocket으로 수신하는 클라이언트입니다.
    시세 TR과 달리 주문 TR은 종목코드 대신 계좌를 등록합니다.
    SC0을 등록하면 SC0~SC4 5개 주문 이벤트가 모두 활성화됩니다.
    내부적으로 _add_real_order_korea()를 호출하여 계좌를 실시간 등록합니다.
"""

from __future__ import annotations

from typing import Callable
from .blocks import SC0RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealSC0():
    """주식주문접수(SC0) 실시간 클라이언트

    EN:
        Manages account registration and message listeners for SC0 real-time
        stock order acceptance data. Registering via on_sc0_message() triggers
        _add_real_order_korea() to register the account with the WebSocket server,
        activating real-time notifications for all SC0-SC4 order events.

    KO:
        SC0 주식주문접수 실시간 데이터의 계좌 등록 및 메시지 리스너를 관리합니다.
        on_sc0_message() 호출 시 _add_real_order_korea()로 계좌를 WebSocket 서버에
        등록하여 SC0~SC4 전체 주문 이벤트 실시간 알림을 활성화합니다.

    Methods:
        on_sc0_message: 주문접수 데이터 수신 콜백 등록 및 계좌 실시간 등록.
        on_remove_sc0_message: 등록된 주문접수 콜백을 제거합니다.
    """

    def __init__(self, parent: Real):
        self._parent = parent

    def on_sc0_message(self, listener: Callable[[SC0RealResponse], None]):
        """주문접수 데이터 수신 콜백 등록 및 계좌 실시간 등록

        EN:
            Register a callback function that will be invoked whenever SC0 real-time
            order acceptance data is received. Internally calls _add_real_order_korea()
            to register the account with the WebSocket server. Since all five order TRs
            (SC0-SC4) share the same registration, this single call activates order
            acceptance, execution, modification, cancellation, and rejection events.

        KO:
            SC0 실시간 주문접수 데이터가 수신될 때마다 호출될 콜백 함수를 등록합니다.
            내부적으로 _add_real_order_korea()를 호출하여 계좌를 WebSocket 서버에
            실시간 등록합니다. SC0~SC4는 동일한 등록을 공유하므로 이 호출 하나로
            접수/체결/정정/취소/거부 5개 이벤트가 모두 활성화됩니다.

        Parameters:
            listener: SC0RealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능).
                      주문 접수 시마다 호출됩니다.

        Returns:
            WebSocket 메시지 리스너 등록 결과
        """
        self._parent._add_real_order_korea()
        return self._parent._on_message("SC0", listener)

    def on_remove_sc0_message(self):
        """등록된 주문접수 콜백을 제거합니다.

        EN:
            Remove the registered SC0 message listener. Does not unregister the
            account from the WebSocket server (other SC TRs may still be active).

        KO:
            등록된 SC0 메시지 리스너를 제거합니다.
            계좌 WebSocket 등록 해제는 수행하지 않습니다
            (다른 SC TR이 여전히 활성 상태일 수 있습니다).

        Returns:
            WebSocket 메시지 리스너 제거 결과
        """
        return self._parent._on_remove_message("SC0")
