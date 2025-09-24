from __future__ import annotations

from typing import Callable
from .blocks import AS2RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_stock.real import Real


class RealAS2():
    def __init__(self, parent: Real):
        self._parent = parent

    def on_as2_message(self, listener: Callable[[AS2RealResponse], None]):
        self._parent._add_real_order()
        return self._parent._on_message("AS2", listener)

    def on_remove_as2_message(self):
        return self._parent._on_remove_message("AS2")
