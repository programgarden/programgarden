
from typing import Optional

from programgarden_core.korea_alias import require_korean_alias
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

from . import t1631, t1632, t1633, t1636, t1637
from .t1631 import TrT1631
from .t1631.blocks import T1631InBlock, T1631Request, T1631RequestHeader
from .t1632 import TrT1632
from .t1632.blocks import T1632InBlock, T1632Request, T1632RequestHeader
from .t1633 import TrT1633
from .t1633.blocks import T1633InBlock, T1633Request, T1633RequestHeader
from .t1636 import TrT1636
from .t1636.blocks import T1636InBlock, T1636Request, T1636RequestHeader
from .t1637 import TrT1637
from .t1637.blocks import T1637InBlock, T1637Request, T1637RequestHeader


class Program:
    """Korean stock program-trading domain client.

    Wraps LS Securities OpenAPI endpoints under ``/stock/program``. Currently
    exposes:
        - ``t1631`` — Program trading comprehensive query (거래소 / 코스닥,
          summary aggregates + program trading rows).
        - ``t1632`` — Time-bucketed program-trading trend (KP200/BASIS +
          program flow per time bucket). Supports tr_cont paging
          (date + time cursors).
        - ``t1633`` — Period-based (daily / weekly / monthly) program-
          trading trend over [fdate, tdate]. Supports tr_cont paging
          (date cursor only).
        - ``t1636`` — Program trading flow per symbol.
        - ``t1637`` — Per-symbol program-trading time series, bucketed by
          time (gubun2='0') or by day (gubun2='1'). Supports tr_cont
          paging via a gubun2-aware cursor (time cursor in time mode,
          date cursor in daily mode).

    Korean aliases are exposed for parity with the rest of the SDK
    (``프로그램매매`` on KoreaStock, ``프로그램매매종합조회``,
    ``시간대별프로그램매매추이``, ``기간별프로그램매매추이``,
    ``종목별프로그램매매동향``, and ``종목별프로그램매매추이`` here).
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
    def t1632(
        self,
        body: T1632InBlock,
        header: Optional[T1632RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1632:
        """Return a TrT1632 request handle for the time-bucketed program-trading trend query.

        Returns time-bucketed KP200 index, BASIS, and program-trading flow
        (total / arbitrage / non-arbitrage buy, sell, and net-buy) for KOSPI
        (``gubun='0'``) or KOSDAQ (``gubun='1'``).

        Supports tr_cont continuation paging via ``date`` + ``time`` CTS
        cursors. Use ``occurs_req()`` or ``occurs_req_async()`` to auto-page
        through all time buckets.

        WARNING: ``gubun`` encoding differs from t1631.
        t1632 uses ``'0'`` for KOSPI (거래소) and ``'1'`` for KOSDAQ.
        t1631 uses ``'1'`` for 거래소 and ``'2'`` for KOSDAQ.

        Args:
            body: ``T1632InBlock`` — gubun (market: '0'=거래소, '1'=코스닥),
                gubun1 (amount/qty: '0'=금액, '1'=수량),
                gubun2 (prior-period change, fixed '1'),
                gubun3 (prior-day flag, fixed '1'),
                date / time (empty for first request; CTS cursors for paging),
                exchgubun ('K'/'N'/'U', default 'K').
            header: Optional request header overrides.
            options: Optional setup options (rate limit, retry behavior).

        Returns:
            TrT1632 — call ``.req()`` for a single page or ``.occurs_req()``
            to auto-page through all time buckets.
        """

        request_data = T1632Request(
            body={
                "t1632InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1632(request_data)

    시간대별프로그램매매추이 = t1632
    시간대별프로그램매매추이.__doc__ = (
        "Query time-bucketed KP200/BASIS and program-trading flow (total / "
        "arbitrage / non-arbitrage) per time bucket for KOSPI or KOSDAQ. "
        "Supports tr_cont auto-paging via occurs_req()."
    )

    @require_korean_alias
    def t1633(
        self,
        body: T1633InBlock,
        header: Optional[T1633RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1633:
        """Return a TrT1633 request handle for the period-based program-trading trend query.

        Returns daily / weekly / monthly program-trading flow (KP200 jisu,
        sign, change, total / arbitrage / non-arbitrage buy, sell, net-buy,
        and volume) over an [fdate, tdate] period for KOSPI (``gubun='0'``)
        or KOSDAQ (``gubun='1'``). The period unit is selected by ``gubun3``
        (``'1'`` daily / ``'2'`` weekly / ``'3'`` monthly).

        Supports tr_cont continuation paging via a SINGLE ``date`` CTS
        cursor (unlike t1632 which uses date + time). First request must
        send ``date=' '`` (single space) per the LS official example
        payload — this is the default value on ``T1633InBlock``.

        WARNING: ``gubun`` encoding matches t1632 (``'0'`` = 거래소,
        ``'1'`` = 코스닥) but is OPPOSITE of t1631 (``'1'`` = 거래소,
        ``'2'`` = 코스닥). ``gubun2`` and ``gubun3`` enum domains differ
        from t1632 (which fixes both at ``Literal['1']``) — see
        ``T1633InBlock`` for the full enum lists. ``fdate`` / ``tdate``
        are validated by ``pattern=r"^\\d{8}$"`` (8 numeric digits).

        Args:
            body: ``T1633InBlock`` — gubun (market: '0'=거래소, '1'=코스닥),
                gubun1 (amount/qty: '0'=금액, '1'=수량),
                gubun2 (value/cumulative: '0'=수치, '1'=누적),
                gubun3 (period unit: '1'=일, '2'=주, '3'=월),
                fdate / tdate (YYYYMMDD period bounds, 8 numeric digits),
                gubun4 ('0'=Default, '1'=직전대비증감),
                date (continuation cursor; default ' ' for first request),
                exchgubun ('K'/'N'/'U', default 'K').
            header: Optional request header overrides.
            options: Optional setup options (rate limit, retry behavior).

        Returns:
            TrT1633 — call ``.req()`` for a single page or ``.occurs_req()``
            to auto-page through the whole period.
        """

        request_data = T1633Request(
            body={
                "t1633InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1633(request_data)

    기간별프로그램매매추이 = t1633
    기간별프로그램매매추이.__doc__ = (
        "Query period-based (daily / weekly / monthly) program-trading flow "
        "on KOSPI / KOSDAQ over an [fdate, tdate] period. Supports tr_cont "
        "auto-paging via occurs_req() with a single date cursor."
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

    @require_korean_alias
    def t1637(
        self,
        body: T1637InBlock,
        header: Optional[T1637RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1637:
        """Return a TrT1637 request handle for per-symbol program-trading time series.

        Returns the program-trading flow (price, change, percent change, volume,
        plus buy / sell / net-buy amount and quantity) for one Korean stock,
        bucketed by time (``gubun2='0'``) or by day (``gubun2='1'``).

        Supports tr_cont continuation paging via a single cursor selected by
        ``gubun2``: time cursor in time mode, date cursor in daily mode.
        ``cts_idx`` is described in the LS spec as a chart-query marker
        (``IDXCTS(9999:차트)``); it is fixed at 9999 by default and is not
        used for continuation paging by this SDK (the date / time cursors
        are used per LS spec).

        Args:
            body: ``T1637InBlock`` — gubun1 (qty/amount), gubun2 (time/daily mode),
                shcode (6-digit stock code), date / time (continuation cursors,
                empty on first request), cts_idx (chart marker, default 9999),
                exchgubun ('K'/'N'/'U', default 'K').
            header: Optional request header overrides.
            options: Optional setup options (rate limit, retry behavior).

        Returns:
            TrT1637 — call ``.req()`` for a single page or ``.occurs_req()``
            to auto-page through the whole time series.
        """

        request_data = T1637Request(
            body={
                "t1637InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1637(request_data)

    종목별프로그램매매추이 = t1637
    종목별프로그램매매추이.__doc__ = (
        "Query per-symbol program-trading time series (price, change, buy / sell / "
        "net-buy amount and quantity) bucketed by time or day. Supports tr_cont "
        "auto-paging via occurs_req() with a gubun2-aware cursor."
    )


__all__ = [
    Program,
    t1631,
    t1632,
    t1633,
    t1636,
    t1637,
]
