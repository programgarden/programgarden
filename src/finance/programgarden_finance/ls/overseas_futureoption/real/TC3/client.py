from __future__ import annotations

from typing import Callable
from .blocks import TC3RealResponse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programgarden_finance.ls.overseas_futureoption.real import Real


class RealTC3():
    def __init__(self, parent: Real):
        self._parent = parent

    def on_tc3_message(self, listener: Callable[[TC3RealResponse], None]):
        self._parent._add_real_order()
        return self._parent._on_message("TC3", listener)

    def on_remove_tc3_message(self):
        return self._parent._on_remove_message("TC3")
