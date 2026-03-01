"""업종지수(IJ_) 실시간 클라이언트

EN:
    Client class for subscribing to and receiving real-time sector/industry index
    data via WebSocket.
    Supports KOSPI ('001'), KOSDAQ ('301'), and other sector index codes.
    Provides index value, change rate, rising/falling stock counts,
    and foreign/institutional net trading data.

KO:
    업종지수의 실시간 데이터를 WebSocket으로 구독/수신하는 클라이언트입니다.
    KOSPI('001'), KOSDAQ('301') 등 업종코드를 등록하면 해당 업종의 지수 데이터가
    실시간으로 수신됩니다. 지수값, 등락률, 상승/하락 종목수, 외인/기관 순매수 등
    25개 필드를 제공합니다.
"""

from __future__ import annotations

from typing import Callable, List
from .blocks import IJ_RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealIJ_():
    """업종지수(IJ_) 실시간 클라이언트

    EN:
        Manages sector code subscriptions and message listeners for IJ_ real-time
        sector/industry index data.
        Each subscription corresponds to one sector code (e.g., '001' for KOSPI).

    KO:
        IJ_ 업종지수 실시간 데이터의 업종코드 구독 및 메시지 리스너를 관리합니다.
        업종코드 하나당 하나의 구독이 생성됩니다 (예: '001' = KOSPI).

    Methods:
        add_ij__symbols: 업종코드를 실시간 지수 구독에 등록합니다.
        remove_ij__symbols: 업종코드를 실시간 지수 구독에서 해제합니다.
        on_ij__message: 지수 데이터 수신 시 호출될 콜백을 등록합니다.
        on_remove_ij__message: 등록된 콜백을 제거합니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_ij__symbols(self, symbols: List[str]):
        """업종코드를 실시간 지수 구독에 등록합니다.

        EN:
            Subscribe to real-time sector index data for the given sector codes.
            Common codes: '001' (KOSPI), '301' (KOSDAQ), '002' (KOSPI 대형주),
            '003' (KOSPI 중형주), '004' (KOSPI 소형주).

        KO:
            지정한 업종코드들의 실시간 지수 데이터 수신을 시작합니다.
            주요 업종코드: '001'(KOSPI), '301'(KOSDAQ), '002'(KOSPI 대형주),
            '003'(KOSPI 중형주), '004'(KOSPI 소형주).

        Parameters:
            symbols: 구독할 업종코드 리스트 (예: ['001', '301'])
        """
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="IJ_")

    def remove_ij__symbols(self, symbols: List[str]):
        """업종코드를 실시간 지수 구독에서 해제합니다.

        EN:
            Unsubscribe from real-time sector index data for the given sector codes.

        KO:
            지정한 업종코드들의 실시간 지수 데이터 수신을 중단합니다.

        Parameters:
            symbols: 해제할 업종코드 리스트 (예: ['001', '301'])
        """
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="IJ_")

    def on_ij__message(self, listener: Callable[[IJ_RealResponse], None]):
        """업종지수 데이터 수신 시 호출될 콜백을 등록합니다.

        EN:
            Register a callback function that will be invoked whenever
            IJ_ real-time sector index data is received.
            The callback receives an IJ_RealResponse containing index value,
            change rate, volume, rising/falling stock counts, and more.

        KO:
            IJ_ 실시간 업종지수 데이터가 수신될 때마다 호출될 콜백 함수를 등록합니다.
            콜백은 지수값, 등락률, 거래량, 상승/하락종목수, 외인/기관 순매수 등
            25개 필드가 담긴 IJ_RealResponse를 인자로 받습니다.

        Parameters:
            listener: IJ_RealResponse를 인자로 받는 콜백 함수 (동기/비동기 모두 가능)
        """
        return self._parent._on_message("IJ_", listener)

    def on_remove_ij__message(self):
        """등록된 업종지수 콜백을 제거합니다.

        EN:
            Remove the registered IJ_ message listener.

        KO:
            등록된 IJ_ 메시지 리스너를 제거합니다.
        """
        return self._parent._on_remove_message("IJ_")
