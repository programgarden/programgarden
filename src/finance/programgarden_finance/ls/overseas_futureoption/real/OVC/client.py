from __future__ import annotations

from typing import Callable, List
from .blocks import OVCRealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_futureoption.real import Real


class RealOVC():
    def __init__(self, parent: Real):
        self._parent = parent

    def add_ovc_symbols(self, symbols: List[str]):
        return self._parent._add_message_symbols(symbols=symbols, tr_cd="OVC")

    def remove_ovc_symbols(self, symbols: List[str]):
        return self._parent._remove_message_symbols(symbols=symbols, tr_cd="OVC")

    def on_ovc_message(self, listener: Callable[[OVCRealResponse], None]):
        return self._parent._on_message("OVC", listener)

    def on_remove_ovc_message(self):
        return self._parent._on_remove_message("OVC")
