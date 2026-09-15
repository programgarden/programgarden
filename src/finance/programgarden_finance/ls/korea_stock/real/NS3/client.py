"""NXT quote subscriptions only; this client does not submit orders."""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from .blocks import NS3RealRequestBody, NS3RealResponse

if TYPE_CHECKING:
    from programgarden_finance.ls.korea_stock.real import Real


class RealNS3:
    def __init__(self, parent: Real):
        self._parent = parent

    @staticmethod
    def _keys(symbols: list[str]) -> list[str]:
        # Validate the entire batch before the parent mutates subscription state.
        return list(dict.fromkeys(NS3RealRequestBody(tr_key=s).tr_key for s in symbols))

    def add_ns3_symbols(self, symbols: list[str]):
        """Subscribe using N-prefixed codes, e.g. N010950 or N010950 + spaces."""
        return self._parent._add_message_symbols(symbols=self._keys(symbols), tr_cd="NS3")

    def remove_ns3_symbols(self, symbols: list[str]):
        """Unsubscribe the same normalized keys retained for reconnection."""
        return self._parent._remove_message_symbols(symbols=self._keys(symbols), tr_cd="NS3")

    def on_ns3_message(self, listener: Callable[[NS3RealResponse], None]):
        return self._parent._on_message("NS3", listener)

    def on_remove_ns3_message(self, listener=None):
        return self._parent._on_remove_message("NS3", listener)
