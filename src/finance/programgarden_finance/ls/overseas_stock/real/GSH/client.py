from __future__ import annotations

from typing import Callable, List
from .blocks import GSHRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_stock.real import Real


class RealGSH():
    """
    해외주식 실시간 호가(GSH) WebSocket 클라이언트

    ⚠️ LS증권 API 제약 (해외주식 한정):
    - 호가 가격(offerho/bidho 1~10)은 정상 제공
    - 개별 호가단계 잔량(offerrem/bidrem 2~10)은 항상 0 (미제공)
    - offerrem1/bidrem1은 총잔량(totofferrem/totbidrem)과 동일한 값
    - 호가 건수(offerno/bidno 1~10)는 항상 0 (미제공)
    - 2026-10-15 03:16 KST(미국 정규장) AAPL 관측: 실시간 15건 모두 위 모양이었고,
      같은 시점 REST g3106 1회도 1호가에만 잔량(=매도·매수 잔량 합계)이 있고
      2~10호가 잔량·건수는 0 이었다. g3106 으로 단계별 잔량을 얻을 수 있다고
      보지 마세요. 한 종목·한 시점 관측이며 다른 종목·세션은 아직 확인 전입니다.
    """
    def __init__(self, parent: Real):
        self._parent = parent

    def add_gsh_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="GSH")

    def remove_gsh_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="GSH")

    def on_gsh_message(self, listener: Callable[[GSHRealResponse], None]):
        return self._parent._on_message("GSH", listener)

    def on_remove_gsh_message(self, listener=None):
        return self._parent._on_remove_message("GSH", listener)
