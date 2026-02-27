"""(NXT) VI발동해제(NVI) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time NXT (Next Trading System)
    VI (Volatility Interruption) trigger/release events via WebSocket.
    The tr_key must be 10 characters: 'N' + 6-digit stock code + 3 trailing spaces,
    which is handled automatically by the NVIRealRequestBody validator.
    Pass '0000000000' (10 zeros) to receive VI events for all NXT stocks.

KO:
    NXT(넥스트거래소) VI(변동성완화장치) 발동/해제 이벤트를 WebSocket으로
    구독/수신하는 클라이언트입니다.
    tr_key는 'N' + 종목코드 6자리 + 공백 3자리 = 10자리로 자동 패딩됩니다.
    '0000000000'(0 10개)을 지정하면 NXT 전 종목 VI 이벤트를 수신합니다.
    가격 필드는 int 타입이며 거래소별단축코드(ex_shcode) 필드를 추가로 제공합니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import NVIRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealNVI():
    """(NXT) VI발동해제(NVI) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for NVI real-time
        NXT VI (Volatility Interruption) events.
        Symbols are automatically padded to 10 characters (e.g., 'N000880' → 'N000880   ').
        Use '0000000000' to subscribe to all NXT stocks at once.

    KO:
        NVI NXT VI 발동/해제 실시간 이벤트의 종목 구독 및 메시지 리스너를 관리합니다.
        종목코드는 자동으로 10자리로 패딩됩니다 (예: 'N000880' → 'N000880   ').
        '0000000000'을 사용하면 NXT 전 종목의 VI 이벤트를 한 번에 수신합니다.

    Methods:
        add_nvi_symbols: NXT 종목코드를 VI발동해제 구독에 등록합니다.
        remove_nvi_symbols: NXT 종목코드를 VI발동해제 구독에서 해제합니다.
        on_nvi_message: VI 이벤트 수신 시 호출될 콜백을 등록합니다.
        on_remove_nvi_message: 등록된 콜백을 제거합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_nvi_symbols(self, symbols: List[str]):
        """NXT 종목코드를 VI발동해제 구독에 등록합니다.

        EN:
            Subscribe to real-time NXT VI trigger/release events for the given symbols.
            Symbols shorter than 10 characters are automatically right-padded with spaces
            (e.g., 'N000880' → 'N000880   ').
            Pass '0000000000' to receive VI events for all NXT stocks simultaneously.

        KO:
            지정한 NXT 종목코드들의 VI 발동/해제 이벤트 수신을 시작합니다.
            10자리 미만의 종목코드는 자동으로 공백으로 우측 패딩됩니다
            (예: 'N000880' → 'N000880   ').
            '0000000000'을 지정하면 NXT 전 종목의 VI 이벤트를 수신합니다.

        Parameters:
            symbols: 구독할 NXT 종목코드 리스트 (예: ['N000880']) 또는 전체 ['0000000000']
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="NVI")

    def remove_nvi_symbols(self, symbols: List[str]):
        """NXT 종목코드를 VI발동해제 구독에서 해제합니다.

        EN:
            Unsubscribe from real-time NXT VI events for the given symbols.

        KO:
            지정한 NXT 종목코드들의 VI 발동/해제 이벤트 수신을 중단합니다.

        Parameters:
            symbols: 해제할 NXT 종목코드 리스트 (예: ['N000880'])
        """
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="NVI")

    def on_nvi_message(self, listener: Callable[[NVIRealResponse], None]):
        """NXT VI 이벤트 수신 시 호출될 콜백을 등록합니다.

        EN:
            Register a callback function that will be invoked whenever
            an NXT VI trigger or release event is received.
            The callback receives an NVIRealResponse containing VI type
            (0:release, 1:static, 2:dynamic, 3:static&dynamic),
            reference prices (int), trigger price (int), stock code,
            time, exchange name, and exchange-specific short code.

        KO:
            NXT VI 발동/해제 이벤트가 수신될 때마다 호출될 콜백 함수를 등록합니다.
            콜백은 VI구분(0:해제, 1:정적, 2:동적, 3:정적&동적), 발동기준가격(int),
            발동가격(int), 종목코드, 시간, 거래소명, 거래소별단축코드 등
            9개 필드가 담긴 NVIRealResponse를 인자로 받습니다.

        Parameters:
            listener: NVIRealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능)
        """
        return self._parent._on_message("NVI", listener)

    def on_remove_nvi_message(self):
        """등록된 NXT VI발동해제 콜백을 제거합니다.

        EN:
            Remove the registered NVI message listener.

        KO:
            등록된 NVI 메시지 리스너를 제거합니다.
        """
        return self._parent._on_remove_message("NVI")
