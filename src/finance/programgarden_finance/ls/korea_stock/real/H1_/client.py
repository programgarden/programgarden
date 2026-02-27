"""KOSPI 호가잔량(H1_) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time KOSPI order book
    (10-level bid/ask) data via WebSocket.

KO:
    KOSPI 종목의 실시간 10단계 호가잔량 데이터를 WebSocket으로 구독/수신하는 클라이언트입니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import H1_RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealH1_():
    """KOSPI 호가잔량(H1_) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for H1_ real-time
        KOSPI order book data.

    KO:
        H1_ KOSPI 호가잔량 실시간 데이터의 종목 구독 및 메시지 리스너를 관리합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_h1__symbols(self, symbols: List[str]):
        """KOSPI 종목을 실시간 호가잔량 구독에 등록합니다.

        Parameters:
            symbols: 구독할 KOSPI 종목 단축코드 리스트 (예: ['005930'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="H1_")

    def remove_h1__symbols(self, symbols: List[str]):
        """KOSPI 종목을 실시간 호가잔량 구독에서 해제합니다."""
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="H1_")

    def on_h1__message(self, listener: Callable[[H1_RealResponse], None]):
        """KOSPI 호가잔량 데이터 수신 시 호출될 콜백을 등록합니다.

        Parameters:
            listener: H1_RealResponse를 인자로 받는 콜백 함수
        """
        return self._parent._on_message("H1_", listener)

    def on_remove_h1__message(self):
        """등록된 KOSPI 호가잔량 콜백을 제거합니다."""
        return self._parent._on_remove_message("H1_")
