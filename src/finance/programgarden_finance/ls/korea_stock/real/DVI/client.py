"""시간외단일가 VI발동해제(DVI) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time KRX VI
    (Volatility Interruption) trigger/release events via WebSocket.
    Notifies when a static VI, dynamic VI, or both are triggered or released
    for KRX-listed stocks during after-hours single-price trading sessions.

KO:
    KRX 시간외단일가 VI(변동성완화장치) 발동/해제 이벤트를 WebSocket으로
    구독/수신하는 클라이언트입니다.
    종목코드 또는 '000000'(전 종목)을 등록하면 해당 종목의 VI 발동/해제 시
    실시간으로 알림을 수신합니다. 정적/동적/정적&동적 VI 구분, 기준가격,
    발동가격 등 8개 필드를 제공합니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import DVIRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealDVI():
    """시간외단일가 VI발동해제(DVI) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for DVI real-time
        KRX VI (Volatility Interruption) events during after-hours trading.
        Use '000000' as symbol to receive VI events for all stocks at once.

    KO:
        DVI 시간외단일가 VI 발동/해제 실시간 이벤트의 종목 구독 및 메시지 리스너를 관리합니다.
        종목코드로 '000000'을 사용하면 전 종목의 VI 이벤트를 한 번에 수신할 수 있습니다.

    Methods:
        add_dvi_symbols: 종목코드를 VI발동해제 구독에 등록합니다.
        remove_dvi_symbols: 종목코드를 VI발동해제 구독에서 해제합니다.
        on_dvi_message: VI 이벤트 수신 시 호출될 콜백을 등록합니다.
        on_remove_dvi_message: 등록된 콜백을 제거합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_dvi_symbols(self, symbols: List[str]):
        """종목코드를 시간외단일가 VI발동해제 구독에 등록합니다.

        EN:
            Subscribe to real-time KRX VI trigger/release events for the given symbols.
            Pass '000000' to receive VI events for all stocks simultaneously.

        KO:
            지정한 종목코드들의 시간외단일가 VI 발동/해제 이벤트 수신을 시작합니다.
            '000000'을 지정하면 상장된 전 종목의 VI 이벤트를 수신합니다.

        Parameters:
            symbols: 구독할 종목 단축코드 리스트 (예: ['086520']) 또는 전체 ['000000']
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="DVI")

    def remove_dvi_symbols(self, symbols: List[str]):
        """종목코드를 시간외단일가 VI발동해제 구독에서 해제합니다.

        EN:
            Unsubscribe from real-time KRX VI events for the given symbols.

        KO:
            지정한 종목코드들의 시간외단일가 VI 발동/해제 이벤트 수신을 중단합니다.

        Parameters:
            symbols: 해제할 종목 단축코드 리스트 (예: ['086520'])
        """
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="DVI")

    def on_dvi_message(self, listener: Callable[[DVIRealResponse], None]):
        """시간외단일가 VI 이벤트 수신 시 호출될 콜백을 등록합니다.

        EN:
            Register a callback function that will be invoked whenever
            a KRX VI trigger or release event is received.
            The callback receives a DVIRealResponse containing VI type
            (0:release, 1:static, 2:dynamic, 3:static&dynamic),
            reference prices, trigger price, stock code, and time.

        KO:
            시간외단일가 VI 발동/해제 이벤트가 수신될 때마다 호출될 콜백 함수를 등록합니다.
            콜백은 VI구분(0:해제, 1:정적, 2:동적, 3:정적&동적), 발동기준가격,
            발동가격, 종목코드, 시간 등 8개 필드가 담긴 DVIRealResponse를 인자로 받습니다.

        Parameters:
            listener: DVIRealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능)
        """
        return self._parent._on_message("DVI", listener)

    def on_remove_dvi_message(self):
        """등록된 시간외단일가 VI발동해제 콜백을 제거합니다.

        EN:
            Remove the registered DVI message listener.

        KO:
            등록된 DVI 메시지 리스너를 제거합니다.
        """
        return self._parent._on_remove_message("DVI")
