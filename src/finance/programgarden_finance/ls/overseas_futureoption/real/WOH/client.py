from __future__ import annotations

from typing import Callable, List
from .blocks import WOHRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_futureoption.real import Real


class RealWOH():
    def __init__(self, parent: Real):
        self._parent = parent

    def add_woh_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="WOH")

    def remove_woh_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="WOH")

    def on_woh_message(self, listener: Callable[[WOHRealResponse], None]):
        return self._parent._on_message("WOH", listener)

    def on_remove_woh_message(self):
        return self._parent._on_remove_message("WOH")
