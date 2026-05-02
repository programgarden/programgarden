
from typing import Optional

from programgarden_core.korea_alias import require_korean_alias
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

from . import t1636
from .t1636 import TrT1636
from .t1636.blocks import T1636InBlock, T1636Request, T1636RequestHeader


class Program:
    """Korean stock program-trading domain client.

    Wraps LS Securities OpenAPI endpoints under ``/stock/program``. Currently
    exposes:
        - ``t1636`` — Program trading flow per symbol (KOSPI / KOSDAQ).

    Korean aliases are exposed for parity with the rest of the SDK
    (``프로그램매매`` on KoreaStock, ``종목별프로그램매매동향`` here).
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1636(
        self,
        body: T1636InBlock,
        header: Optional[T1636RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1636:
        """Return a TrT1636 request handle for Korean stock program trading by symbol.

        Returns per-symbol program trading flow (program buy/sell quantity and
        amount, net-buy quantity and amount, sort-key weight, market
        capitalization, and the net-buy ratio versus market cap added by LS on
        2026-01-08). Supports IDXCTS-based continuation paging via ``cts_idx``.

        Args:
            body: ``T1636InBlock`` — gubun (market), gubun1 (qty/amount),
                gubun2 (sort key), shcode (stock code), cts_idx (continuation
                index), exchgubun (exchange filter).
            header: Optional request header overrides.
            options: Optional setup options (rate limit, retry behavior).

        Returns:
            TrT1636 — call ``.req()`` for a single page or ``.occurs_req()``
            to auto-page through all results.
        """

        request_data = T1636Request(
            body={
                "t1636InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1636(request_data)

    종목별프로그램매매동향 = t1636
    종목별프로그램매매동향.__doc__ = (
        "Query Korean stock program trading flow by symbol on KOSPI / KOSDAQ "
        "(includes the net-buy ratio versus market cap added by LS on 2026-01-08)."
    )


__all__ = [
    Program,
    t1636,
]
