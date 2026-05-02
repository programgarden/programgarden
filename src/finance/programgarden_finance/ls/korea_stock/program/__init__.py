
from typing import Optional

from programgarden_core.korea_alias import require_korean_alias
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

from . import t1631, t1636
from .t1631 import TrT1631
from .t1631.blocks import T1631InBlock, T1631Request, T1631RequestHeader
from .t1636 import TrT1636
from .t1636.blocks import T1636InBlock, T1636Request, T1636RequestHeader


class Program:
    """Korean stock program-trading domain client.

    Wraps LS Securities OpenAPI endpoints under ``/stock/program``. Currently
    exposes:
        - ``t1631`` — Program trading comprehensive query (거래소 / 코스닥,
          summary aggregates + program trading rows).
        - ``t1636`` — Program trading flow per symbol.

    Korean aliases are exposed for parity with the rest of the SDK
    (``프로그램매매`` on KoreaStock, ``프로그램매매종합조회`` and
    ``종목별프로그램매매동향`` here).
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1631(
        self,
        body: T1631InBlock,
        header: Optional[T1631RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1631:
        """Return a TrT1631 request handle for the program trading comprehensive query.

        Returns Korean stock program trading data:

        - ``T1631Response.summary_block`` — eight scalar order/remainder
          aggregates from the (sell vs buy) × (arbitrage vs non-arbitrage)
          × (unfilled-remaining vs ordered) breakdown documented in the
          LS spec.
        - ``T1631Response.block`` — Object Array of buy / sell / net
          quantity and amount per row as reported by LS. Row meaning and
          array ordering are not documented in the LS public spec.

        Unlike t1636, this TR has **no IDXCTS continuation** — a single
        response covers either the same-day query or the period query.

        Args:
            body: ``T1631InBlock`` — gubun (market: '1'=거래소, '2'=코스닥),
                dgubun (date mode: '1'=당일조회, '2'=기간조회),
                sdate / edate (length 8; may be empty when dgubun='1'),
                exchgubun ('K'/'N'/'U').
            header: Optional request header overrides.
            options: Optional setup options (rate limit, retry behavior).

        Returns:
            TrT1631 — call ``.req()`` or ``.req_async()``. No
            ``occurs_req`` method (no continuation).
        """

        request_data = T1631Request(
            body={
                "t1631InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1631(request_data)

    프로그램매매종합조회 = t1631
    프로그램매매종합조회.__doc__ = (
        "Query Korean stock program trading (eight scalar order/remainder "
        "aggregates plus a program trading row array)."
    )

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
    t1631,
    t1636,
]
