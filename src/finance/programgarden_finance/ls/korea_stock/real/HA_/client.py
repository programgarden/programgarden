"""KOSDAQ 호가잔량(HA_) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time KOSDAQ order book
    data via WebSocket.

KO:
    KOSDAQ 종목의 실시간 10단계 호가잔량 데이터를 WebSocket으로 구독/수신하는 클라이언트입니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import HA_RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealHA_():
    """KOSDAQ 호가잔량(HA_) 실시간 클라이언트"""
    def __init__(self, parent: Real):
        self._parent = parent

    def add_ha__symbols(self, symbols: List[str]):
        """KOSDAQ 종목을 실시간 호가잔량 구독에 등록합니다.

        Parameters:
            symbols: 구독할 KOSDAQ 종목 단축코드 리스트 (예: ['086520'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="HA_")

    def remove_ha__symbols(self, symbols: List[str]):
        """KOSDAQ 종목을 실시간 호가잔량 구독에서 해제합니다."""
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="HA_")

    def on_ha__message(self, listener: Callable[[HA_RealResponse], None]):
        """KOSDAQ 호가잔량 데이터 수신 시 호출될 콜백을 등록합니다.

        Parameters:
            listener: HA_RealResponse를 인자로 받는 콜백 함수
        """
        return self._parent._on_message("HA_", listener)

    def on_remove_ha__message(self):
        """등록된 KOSDAQ 호가잔량 콜백을 제거합니다."""
        return self._parent._on_remove_message("HA_")
