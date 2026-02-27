"""KOSPI 체결(S3_) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time KOSPI trade
    execution data via WebSocket.

KO:
    KOSPI 종목의 실시간 체결 데이터를 WebSocket으로 구독/수신하는 클라이언트입니다.
    종목코드를 등록하면 해당 종목의 체결 데이터가 실시간으로 수신됩니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import S3_RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealS3_():
    """KOSPI 체결(S3_) 실시간 클라이언트

    EN:
        Manages symbol subscriptions and message listeners for S3_ real-time
        KOSPI trade execution data.

    KO:
        S3_ KOSPI 체결 실시간 데이터의 종목 구독 및 메시지 리스너를 관리합니다.

    Methods:
        add_s3__symbols: 종목코드를 실시간 구독에 등록합니다.
        remove_s3__symbols: 종목코드를 실시간 구독에서 해제합니다.
        on_s3__message: 체결 데이터 수신 시 호출될 콜백을 등록합니다.
        on_remove_s3__message: 등록된 콜백을 제거합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_s3__symbols(self, symbols: List[str]):
        """KOSPI 종목을 실시간 체결 구독에 등록합니다.

        EN:
            Subscribe to real-time trade execution data for the given KOSPI symbols.

        KO:
            지정한 KOSPI 종목코드들의 실시간 체결 데이터 수신을 시작합니다.

        Parameters:
            symbols: 구독할 KOSPI 종목 단축코드 리스트 (예: ['005930', '000660'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="S3_")

    def remove_s3__symbols(self, symbols: List[str]):
        """KOSPI 종목을 실시간 체결 구독에서 해제합니다.

        EN:
            Unsubscribe from real-time trade execution data for the given KOSPI symbols.

        KO:
            지정한 KOSPI 종목코드들의 실시간 체결 데이터 수신을 중단합니다.

        Parameters:
            symbols: 해제할 KOSPI 종목 단축코드 리스트
        """
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="S3_")

    def on_s3__message(self, listener: Callable[[S3_RealResponse], None]):
        """KOSPI 체결 데이터 수신 시 호출될 콜백을 등록합니다.

        EN:
            Register a callback function that will be invoked whenever
            S3_ real-time trade data is received.

        KO:
            S3_ 실시간 체결 데이터가 수신될 때마다 호출될 콜백 함수를 등록합니다.

        Parameters:
            listener: S3_RealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능)
        """
        return self._parent._on_message("S3_", listener)

    def on_remove_s3__message(self):
        """등록된 KOSPI 체결 콜백을 제거합니다.

        EN:
            Remove the registered S3_ message listener.

        KO:
            등록된 S3_ 메시지 리스너를 제거합니다.
        """
        return self._parent._on_remove_message("S3_")
