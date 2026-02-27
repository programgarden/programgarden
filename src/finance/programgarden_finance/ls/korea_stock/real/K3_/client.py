"""KOSDAQ 체결(K3_) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time KOSDAQ trade
    execution data via WebSocket.

KO:
    KOSDAQ 종목의 실시간 체결 데이터를 WebSocket으로 구독/수신하는 클라이언트입니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import K3_RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealK3_():
    """KOSDAQ 체결(K3_) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for K3_ real-time
        KOSDAQ trade execution data.

    KO:
        K3_ KOSDAQ 체결 실시간 데이터의 종목 구독 및 메시지 리스너를 관리합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_k3__symbols(self, symbols: List[str]):
        """KOSDAQ 종목을 실시간 체결 구독에 등록합니다.

        Parameters:
            symbols: 구독할 KOSDAQ 종목 단축코드 리스트 (예: ['122870'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="K3_")

    def remove_k3__symbols(self, symbols: List[str]):
        """KOSDAQ 종목을 실시간 체결 구독에서 해제합니다."""
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="K3_")

    def on_k3__message(self, listener: Callable[[K3_RealResponse], None]):
        """KOSDAQ 체결 데이터 수신 시 호출될 콜백을 등록합니다.

        Parameters:
            listener: K3_RealResponse를 인자로 받는 콜백 함수
        """
        return self._parent._on_message("K3_", listener)

    def on_remove_k3__message(self):
        """등록된 KOSDAQ 체결 콜백을 제거합니다."""
        return self._parent._on_remove_message("K3_")
