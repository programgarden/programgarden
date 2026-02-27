"""(NXT) 호가잔량(NH1) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time NXT (Next Trading System)
    10-level order book (bid/ask) data via WebSocket.
    The tr_key must be 10 characters: 'N' + 6-digit stock code + 3 trailing spaces,
    which is handled automatically by the NH1RealRequestBody validator.
    All price and quantity fields in the response use int type.

KO:
    NXT(넥스트거래소) 종목의 실시간 10단계 호가잔량 데이터를 WebSocket으로
    구독/수신하는 클라이언트입니다.
    tr_key는 'N' + 종목코드 6자리 + 공백 3자리 = 10자리로 자동 패딩됩니다.
    응답의 가격/수량 필드는 모두 int 타입이며 매도/매수 각 10단계 호가,
    총잔량, 중간가격, 거래소별단축코드 등을 제공합니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import NH1RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealNH1():
    """(NXT) 호가잔량(NH1) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for NH1 real-time
        NXT 10-level order book data.
        Symbols are automatically padded to 10 characters (e.g., 'N000880' → 'N000880   ').
        Provides 10-level bid/ask prices (int) and quantities (int), total quantities,
        mid-price, and exchange-specific short code.

    KO:
        NH1 NXT 호가잔량 실시간 데이터의 종목 구독 및 메시지 리스너를 관리합니다.
        종목코드는 자동으로 10자리로 패딩됩니다 (예: 'N000880' → 'N000880   ').
        매도/매수 각 10단계 호가(int)와 잔량(int), 총잔량, 중간가격,
        거래소별단축코드 등을 제공합니다.

    Methods:
        add_nh1_symbols: NXT 종목코드를 실시간 호가잔량 구독에 등록합니다.
        remove_nh1_symbols: NXT 종목코드를 실시간 호가잔량 구독에서 해제합니다.
        on_nh1_message: 호가잔량 데이터 수신 시 호출될 콜백을 등록합니다.
        on_remove_nh1_message: 등록된 콜백을 제거합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_nh1_symbols(self, symbols: List[str]):
        """NXT 종목코드를 실시간 호가잔량 구독에 등록합니다.

        EN:
            Subscribe to real-time NXT 10-level order book data for the given symbols.
            Symbols shorter than 10 characters are automatically right-padded with spaces
            (e.g., 'N000880' → 'N000880   ').
            Format: 'N' + 6-digit KRX stock code + 3 trailing spaces.

        KO:
            지정한 NXT 종목코드들의 실시간 호가잔량 데이터 수신을 시작합니다.
            10자리 미만의 종목코드는 자동으로 공백으로 우측 패딩됩니다
            (예: 'N000880' → 'N000880   ').
            형식: 'N' + KRX 종목코드 6자리 + 공백 3자리.

        Parameters:
            symbols: 구독할 NXT 종목코드 리스트 (예: ['N000880', 'N005930'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="NH1")

    def remove_nh1_symbols(self, symbols: List[str]):
        """NXT 종목코드를 실시간 호가잔량 구독에서 해제합니다.

        EN:
            Unsubscribe from real-time NXT order book data for the given symbols.

        KO:
            지정한 NXT 종목코드들의 실시간 호가잔량 데이터 수신을 중단합니다.

        Parameters:
            symbols: 해제할 NXT 종목코드 리스트 (예: ['N000880'])
        """
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="NH1")

    def on_nh1_message(self, listener: Callable[[NH1RealResponse], None]):
        """호가잔량 데이터 수신 시 호출될 콜백을 등록합니다.

        EN:
            Register a callback function that will be invoked whenever
            NH1 real-time NXT order book data is received.
            The callback receives an NH1RealResponse containing 10 levels of
            bid/ask prices (int) and quantities (int), total bid/ask quantities,
            dynamic/static auction flag, stock code, mid-price, and more.

        KO:
            NH1 실시간 NXT 호가잔량 데이터가 수신될 때마다 호출될 콜백 함수를 등록합니다.
            콜백은 매도/매수 각 10단계 호가(int)와 잔량(int), 총매도/매수잔량,
            동시호가구분, 종목코드, 중간가격, 거래소별단축코드 등이 담긴
            NH1RealResponse를 인자로 받습니다.

        Parameters:
            listener: NH1RealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능)
        """
        return self._parent._on_message("NH1", listener)

    def on_remove_nh1_message(self):
        """등록된 NXT 호가잔량 콜백을 제거합니다.

        EN:
            Remove the registered NH1 message listener.

        KO:
            등록된 NH1 메시지 리스너를 제거합니다.
        """
        return self._parent._on_remove_message("NH1")
