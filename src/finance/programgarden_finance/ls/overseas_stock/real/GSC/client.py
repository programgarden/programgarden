from __future__ import annotations

from typing import Callable, List
from .blocks import GSCRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_stock.real import Real


class RealGSC():
    def __init__(self, parent: Real):
        self._parent = parent

    def add_gsc_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="GSC")

    def remove_gsc_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="GSC")

    def on_gsc_message(self, listener: Callable[[GSCRealResponse], None]):
        return self._parent._on_message("GSC", listener)

    def on_remove_gsc_message(self):
        return self._parent._on_remove_message("GSC")
