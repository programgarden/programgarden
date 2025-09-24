from __future__ import annotations

from typing import Callable
from .blocks import TC1RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_futureoption.real import Real


class RealTC1():
    def __init__(self, parent: Real):
        self._parent = parent

    def on_tc1_message(self, listener: Callable[[TC1RealResponse], None]):
        self._parent._add_real_order()
        return self._parent._on_message("TC1", listener)

    def on_remove_tc1_message(self):
        return self._parent._on_remove_message("TC1")
