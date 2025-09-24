from __future__ import annotations

from typing import Callable, List
from .blocks import WOCRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_futureoption.real import Real


class RealWOC():
    def __init__(self, parent: Real):
        self._parent = parent

    def add_woc_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="WOC")

    def remove_woc_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="WOC")

    def on_woc_message(self, listener: Callable[[WOCRealResponse], None]):
        return self._parent._on_message("WOC", listener)

    def on_remove_woc_message(self):
        return self._parent._on_remove_message("WOC")
