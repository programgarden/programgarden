from __future__ import annotations

from typing import Callable, List
from .blocks import GSHRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_stock.real import Real


class RealGSH():
    def __init__(self, parent: Real):
        self._parent = parent

    def add_gsh_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="GSH")

    def remove_gsh_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="GSH")

    def on_gsh_message(self, listener: Callable[[GSHRealResponse], None]):
        return self._parent._on_message("GSH", listener)

    def on_remove_gsh_message(self):
        return self._parent._on_remove_message("GSH")
