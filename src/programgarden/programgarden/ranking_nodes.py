"""LS ranking reads for KoreaStockRankingNode and OverseasStockRankingNode.

Request values are copied from the SDK examples and the LS OpenAPI guide; none
are inferred:

- t1441 등락율상위: ``gubun1`` market ('0' all, '1' KOSPI, '2' KOSDAQ), ``gubun2``
  ('0' gainers, '1' losers), ``gubun3`` '0' (today). Other fields keep the SDK
  defaults (``example/korea_stock/run_t1441.py``).
- t1452 거래량상위: ``gubun`` market, ``jnilgubun`` '1' (today)
  (``run_t1452.py``).
- t1463 거래대금상위: ``gubun`` market, ``jnilgubun`` '0' (today)
  (``run_t1463.py``).
- t1444 시가총액상위: ``upcode`` '001' (KOSPI composite) or '301' (KOSDAQ
  composite), ``idx`` (``run_t1444.py`` and the t1444 ``upcode`` description).
- g3112 해외주식API시세순위: ``delaygb`` 'R', ``natcode`` 'US', ``exgubun``
  ('1' all, '2' New York, '3' NASDAQ, '4' ETF), ``rankgubun`` '0'-'7',
  ``cts_value`` continuation (LS guide, ``run_g3112.py``).

Values are consumed as returned by LS. Units are named in the row and never
converted. Every LS failure raises ``RankingNodeError`` whose message starts
with the TR code, e.g. ``"t1441: 01234 <message>"``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

MAX_RANKING_REQUESTS = 5
RANKING_LIMIT_MIN = 1
RANKING_LIMIT_MAX = 100
DEFAULT_RANKING_LIMIT = 20

# LS response codes this engine treats as a successful query (see
# database/broker_evidence.py and futures_read_evidence.py).
SUCCESS_CODES = frozenset({"00000", "00136"})

# ── KoreaStockRankingNode ────────────────────────────────────────────────
KOREA_RANKING_TRS: Dict[str, str] = {
    "change_rate_up": "t1441",
    "change_rate_down": "t1441",
    "volume": "t1452",
    "trading_value": "t1463",
    "market_cap": "t1444",
}
# t1441 gubun1 / t1452 gubun / t1463 gubun: '0' all, '1' KOSPI, '2' KOSDAQ.
KOREA_MARKET_CODES: Dict[str, str] = {"all": "0", "KOSPI": "1", "KOSDAQ": "2"}
# t1444 upcode: '001' KOSPI composite, '301' KOSDAQ composite.
KOREA_MARKET_CAP_UPCODES: Dict[str, str] = {"KOSPI": "001", "KOSDAQ": "301"}

# trading_value / market_cap source field and unit per TR. None = the TR has no such field.
KOREA_TRADING_VALUE_UNITS: Dict[str, Optional[str]] = {
    "t1441": "as_returned", "t1452": None, "t1463": "KRW_million", "t1444": None,
}
KOREA_MARKET_CAP_UNITS: Dict[str, Optional[str]] = {
    "t1441": "as_returned", "t1452": None, "t1463": "KRW_million", "t1444": "KRW_100million",
}

# ── OverseasStockRankingNode ─────────────────────────────────────────────
OVERSEAS_RANK_CODES: Dict[str, str] = {
    "change_rate_up": "0",
    "change_rate_down": "1",
    "volume": "2",
    "trading_value": "3",
    "turnover": "4",
    "market_cap": "5",
    "high_52w": "6",
    "low_52w": "7",
}
OVERSEAS_MARKET_CODES: Dict[str, str] = {"all": "1", "NYSE": "2", "NASDAQ": "3", "ETF": "4"}
# LS key symbol prefix → engine exchange label (same map as overseas_stock_exchange_pair).
# 81 covers NYSE and AMEX; it is labelled NYSE, as everywhere else in the engine.
KEYSYMBOL_EXCHANGES: Dict[str, str] = {"81": "NYSE", "82": "NASDAQ"}

# LS sign codes (sibling TR blocks): 1 upper limit, 2 up, 3 unchanged, 4 lower limit, 5 down.
# '+' / '-' are accepted as in executor._ls_signed_change.
_UP_SIGNS = frozenset({"1", "2", "+"})
_DOWN_SIGNS = frozenset({"4", "5", "-"})
_FLAT_SIGNS = frozenset({"3"})


class RankingNodeError(RuntimeError):
    """A ranking read failed. The message starts with the LS TR code."""


@dataclass(frozen=True)
class RankingRequest:
    ranking_type: str
    market: str
    limit: int
    tr_code: str


@dataclass
class RankingPage:
    """One LS response reduced to what paging needs."""

    rows: List[Any]
    more: bool
    cursor: Any = None
    cont_key: str = ""


@dataclass
class RankingResult:
    rows: List[Any] = field(default_factory=list)
    requests: int = 0


def _limit(config: Dict[str, Any], tr_code: str) -> int:
    raw = config.get("limit", DEFAULT_RANKING_LIMIT)
    if raw is None:
        raw = DEFAULT_RANKING_LIMIT
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise RankingNodeError(f"{tr_code}: limit must be a whole number from 1 to 100 (got {raw!r})")
    if not RANKING_LIMIT_MIN <= raw <= RANKING_LIMIT_MAX:
        raise RankingNodeError(f"{tr_code}: limit must be from 1 to 100 (got {raw})")
    return raw


def korea_ranking_request(config: Dict[str, Any]) -> RankingRequest:
    """Validate KoreaStockRankingNode settings. Invalid combinations raise."""
    ranking_type = config.get("ranking_type") or "change_rate_up"
    tr_code = KOREA_RANKING_TRS.get(ranking_type)
    if tr_code is None:
        raise RankingNodeError(
            f"t1441: unsupported ranking_type {ranking_type!r}; choose one of {', '.join(KOREA_RANKING_TRS)}"
        )
    market = config.get("market") or "all"
    if market not in KOREA_MARKET_CODES:
        raise RankingNodeError(f"{tr_code}: unsupported market {market!r}; choose all, KOSPI or KOSDAQ")
    if tr_code == "t1444" and market not in KOREA_MARKET_CAP_UPCODES:
        raise RankingNodeError(
            "t1444: market_cap ranks one market at a time; choose market KOSPI or KOSDAQ (not all)"
        )
    return RankingRequest(ranking_type, market, _limit(config, tr_code), tr_code)


def overseas_ranking_request(config: Dict[str, Any]) -> RankingRequest:
    """Validate OverseasStockRankingNode settings. Invalid values raise."""
    ranking_type = config.get("ranking_type") or "change_rate_up"
    if ranking_type not in OVERSEAS_RANK_CODES:
        raise RankingNodeError(
            f"g3112: unsupported ranking_type {ranking_type!r}; choose one of {', '.join(OVERSEAS_RANK_CODES)}"
        )
    market = config.get("market") or "all"
    if market not in OVERSEAS_MARKET_CODES:
        raise RankingNodeError(f"g3112: unsupported market {market!r}; choose all, NYSE, NASDAQ or ETF")
    return RankingRequest(ranking_type, market, _limit(config, "g3112"), "g3112")


def korea_in_block(request: RankingRequest, idx: int = 0):
    """Build the SDK InBlock for one Korea ranking page (values from SDK examples)."""
    tr = request.tr_code
    if tr == "t1441":
        from programgarden_finance.ls.korea_stock.ranking.t1441.blocks import T1441InBlock
        return T1441InBlock(
            gubun1=KOREA_MARKET_CODES[request.market],
            gubun2="0" if request.ranking_type == "change_rate_up" else "1",
            gubun3="0",
            idx=idx,
        )
    if tr == "t1452":
        from programgarden_finance.ls.korea_stock.ranking.t1452.blocks import T1452InBlock
        return T1452InBlock(gubun=KOREA_MARKET_CODES[request.market], jnilgubun="1", idx=idx)
    if tr == "t1463":
        from programgarden_finance.ls.korea_stock.ranking.t1463.blocks import T1463InBlock
        return T1463InBlock(gubun=KOREA_MARKET_CODES[request.market], jnilgubun="0", idx=idx)
    if tr == "t1444":
        from programgarden_finance.ls.korea_stock.ranking.t1444.blocks import T1444InBlock
        return T1444InBlock(upcode=KOREA_MARKET_CAP_UPCODES[request.market], idx=idx)
    raise RankingNodeError(f"{tr}: no request builder")  # pragma: no cover - guarded by korea_ranking_request


def overseas_in_block(request: RankingRequest, cts_value: str = ""):
    """Build the SDK InBlock for one g3112 page (values from the LS guide)."""
    from programgarden_finance.ls.overseas_stock.market.g3112.blocks import G3112InBlock
    return G3112InBlock(
        delaygb="R",
        natcode="US",
        exgubun=OVERSEAS_MARKET_CODES[request.market],
        rankgubun=OVERSEAS_RANK_CODES[request.ranking_type],
        cts_value=cts_value or "",
    )


def check_response(tr_code: str, response: Any) -> None:
    """Raise unless the LS response is a successful query."""
    if response is None:
        raise RankingNodeError(f"{tr_code}: no response")
    error_msg = (getattr(response, "error_msg", None) or "").strip()
    if error_msg:
        raise RankingNodeError(f"{tr_code}: {error_msg}")
    status = getattr(response, "status_code", None)
    if status is not None and status >= 400:
        raise RankingNodeError(f"{tr_code}: HTTP {status}")
    code = (getattr(response, "rsp_cd", "") or "").strip()
    if code not in SUCCESS_CODES:
        message = (getattr(response, "rsp_msg", "") or "").strip()
        raise RankingNodeError(f"{tr_code}: {code or '(no code)'} {message or '(no message)'}".rstrip())


def _header_more(response: Any) -> Tuple[bool, str]:
    header = getattr(response, "header", None)
    more = (getattr(header, "tr_cont", "") or "").strip().upper() == "Y"
    return more, (getattr(header, "tr_cont_key", "") or "")


def korea_page(tr_code: str, response: Any) -> RankingPage:
    check_response(tr_code, response)
    more, cont_key = _header_more(response)
    cont = getattr(response, "cont_block", None)
    idx = getattr(cont, "idx", None) if cont is not None else None
    return RankingPage(rows=list(getattr(response, "block", None) or []), more=more and bool(idx),
                       cursor=idx, cont_key=cont_key)


def overseas_page(response: Any) -> RankingPage:
    check_response("g3112", response)
    more, cont_key = _header_more(response)
    block = getattr(response, "block", None)
    cts = (getattr(block, "cts_value", "") or "").strip() if block is not None else ""
    return RankingPage(rows=list(getattr(response, "block1", None) or []), more=more and bool(cts),
                       cursor=cts, cont_key=cont_key)


async def collect_pages(
    fetch_page: Callable[[Any, str], Awaitable[RankingPage]],
    *,
    limit: int,
    row_key: Callable[[Any], str],
    max_requests: int = MAX_RANKING_REQUESTS,
) -> RankingResult:
    """Read pages until ``limit`` unique rows, the last page, or ``max_requests``.

    ``fetch_page(cursor, cont_key)`` receives ``(None, "")`` for the first page.
    Rows repeated on a later page (rankings move between requests) keep their
    first position. The SDK rate limiter spaces the requests of one TR.
    """
    result = RankingResult()
    seen = set()
    cursor: Any = None
    cont_key = ""
    while result.requests < max_requests:
        page = await fetch_page(cursor, cont_key)
        result.requests += 1
        for row in page.rows:
            key = row_key(row)
            if not key or key in seen:
                continue
            seen.add(key)
            result.rows.append(row)
        if len(result.rows) >= limit or not page.more:
            break
        cursor, cont_key = page.cursor, page.cont_key
    result.rows = result.rows[:limit]
    return result


def _signed(value: Any, sign: str) -> Any:
    """Apply the LS direction code to a magnitude. Unknown codes keep the raw value."""
    if value is None:
        return None
    if sign in _FLAT_SIGNS:
        return 0 if isinstance(value, int) else 0.0
    if sign in _UP_SIGNS:
        return abs(value)
    if sign in _DOWN_SIGNS:
        return -abs(value)
    return value


def _number(raw: Any, *, integral: bool = False) -> Any:
    """Parse an LS numeric string exactly. Empty or non-numeric values become None."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = Decimal(str(raw))
    else:
        text = str(raw).strip().replace(",", "")
        if not text:
            return None
        try:
            value = Decimal(text)
        except InvalidOperation:
            return None
    if not value.is_finite():
        return None
    if integral and value == value.to_integral_value():
        return int(value)
    return float(value)


def keysymbol_exchange(keysymbol: str, symbol: str) -> Tuple[Optional[str], str]:
    """Exchange from an LS key symbol of the form '81'/'82' + symbol, else unavailable."""
    key = (keysymbol or "").strip()
    sym = (symbol or "").strip()
    prefix = key[:2]
    if sym and prefix in KEYSYMBOL_EXCHANGES and key[2:] == sym:
        return KEYSYMBOL_EXCHANGES[prefix], "keysymbol"
    return None, "unavailable"


class RankingRowBuilder:
    """Row shapes of the ranking nodes (checked against the declared ports)."""

    @staticmethod
    def korea_row(rank: int, item: Any, tr_code: str, market: Optional[str]) -> Dict[str, Any]:
        sign = str(getattr(item, "sign", "") or "").strip()
        trading_value = getattr(item, "value", None) if KOREA_TRADING_VALUE_UNITS[tr_code] else None
        market_cap = getattr(item, "total", None) if KOREA_MARKET_CAP_UNITS[tr_code] else None
        session = tr_code == "t1441"
        return {
            "rank": rank,
            "symbol": str(getattr(item, "shcode", "") or "").strip(),
            "exchange": "KRX",
            "market": market,
            "name": str(getattr(item, "hname", "") or "").strip(),
            "price": getattr(item, "price", None),
            "open": getattr(item, "open", None) if session else None,
            "high": getattr(item, "high", None) if session else None,
            "low": getattr(item, "low", None) if session else None,
            "sign": sign,
            "change": _signed(getattr(item, "change", None), sign),
            "change_pct": _signed(getattr(item, "diff", None), sign),
            "volume": getattr(item, "volume", None),
            "trading_value": trading_value,
            "trading_value_unit": KOREA_TRADING_VALUE_UNITS[tr_code] if trading_value is not None else None,
            "market_cap": market_cap,
            "market_cap_unit": KOREA_MARKET_CAP_UNITS[tr_code] if market_cap is not None else None,
            "product": "korea_stock",
            "source_tr": tr_code,
        }

    @staticmethod
    def korea_symbol(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "exchange": row["exchange"],
            "market": row["market"],
            "symbol": row["symbol"],
            "name": row["name"],
            "product": "korea_stock",
        }

    @staticmethod
    def overseas_row(rank: int, item: Any) -> Dict[str, Any]:
        symbol = str(getattr(item, "symbol", "") or "").strip()
        keysymbol = str(getattr(item, "keysymbol", "") or "").strip()
        exchange, exchange_source = keysymbol_exchange(keysymbol, symbol)
        sign = str(getattr(item, "sign", "") or "").strip()
        trading_value = _number(getattr(item, "amount", None), integral=True)
        market_cap = _number(getattr(item, "shareprc", None), integral=True)
        return {
            "rank": rank,
            "symbol": symbol,
            "exchange": exchange,
            "exchange_source": exchange_source,
            "name": str(getattr(item, "korname", "") or "").strip(),
            "exchange_name": str(getattr(item, "exsymbol", "") or "").strip(),
            "keysymbol": keysymbol,
            "price": _number(getattr(item, "price", None)),
            "sign": sign,
            "change": _signed(_number(getattr(item, "diff", None)), sign),
            "change_pct": _signed(_number(getattr(item, "rate", None)), sign),
            "volume": _number(getattr(item, "volume", None), integral=True),
            "trading_value": trading_value,
            "trading_value_unit": "as_returned" if trading_value is not None else None,
            "turnover": _number(getattr(item, "trgt", None)),
            "market_cap": market_cap,
            "market_cap_unit": "as_returned" if market_cap is not None else None,
            "high_52w": _number(getattr(item, "high52p", None)),
            "low_52w": _number(getattr(item, "low52p", None)),
            "product": "overseas_stock",
            "source_tr": "g3112",
        }

    @staticmethod
    def overseas_symbol(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "exchange": row["exchange"],
            "symbol": row["symbol"],
            "name": row["name"],
            "product": "overseas_stock",
        }


def korea_outputs(request: RankingRequest, items: List[Any]) -> Dict[str, Any]:
    market = None if request.market == "all" else request.market
    rankings = [
        RankingRowBuilder.korea_row(rank, item, request.tr_code, market)
        for rank, item in enumerate(items, 1)
    ]
    symbols = [RankingRowBuilder.korea_symbol(row) for row in rankings if row["symbol"]]
    return {"rankings": rankings, "symbols": symbols, "count": len(rankings)}


def overseas_outputs(items: List[Any]) -> Dict[str, Any]:
    rankings = [RankingRowBuilder.overseas_row(rank, item) for rank, item in enumerate(items, 1)]
    symbols = [RankingRowBuilder.overseas_symbol(row) for row in rankings if row["exchange"] and row["symbol"]]
    return {"rankings": rankings, "symbols": symbols, "count": len(rankings)}


# ── Deep validation / dry run (no broker call) ───────────────────────────
@dataclass(frozen=True)
class _SyntheticKoreaRow:
    shcode: str
    hname: str
    price: int
    sign: str
    change: int
    diff: float
    volume: int
    open: int
    high: int
    low: int
    value: int
    total: int


@dataclass(frozen=True)
class _SyntheticOverseasRow:
    keysymbol: str
    exsymbol: str
    symbol: str
    korname: str
    price: str
    sign: str
    diff: str
    rate: str
    volume: str
    amount: str
    trgt: str
    shareprc: str
    high52p: str
    low52p: str


_SYNTHETIC_KOREA = (
    # price > open on the first two rows so guide filters (e.g. 3-15 % and above the open)
    # have a candidate during offline validation.
    _SyntheticKoreaRow("005930", "삼성전자", 61000, "2", 3000, 5.17, 15000000, 59800, 61200, 59700, 910000, 3640000),
    _SyntheticKoreaRow("000660", "SK하이닉스", 182000, "2", 6000, 3.41, 3200000, 179500, 183000, 179000, 580000, 1325000),
    _SyntheticKoreaRow("035420", "NAVER", 171500, "5", 1500, 0.87, 650000, 173000, 173500, 170500, 112000, 281000),
)

_SYNTHETIC_OVERSEAS = (
    _SyntheticOverseasRow("82AAPL", "나스닥 AAPL", "AAPL", "애플", "228.500000", "2", "3.100000", "1.38",
                          "52000000", "11900000", "0.340000", "3450000000", "237.230000", "164.080000"),
    _SyntheticOverseasRow("82MSFT", "나스닥 MSFT", "MSFT", "마이크로소프트", "415.200000", "2", "2.050000", "0.50",
                          "21000000", "8700000", "0.280000", "3090000000", "468.350000", "362.900000"),
    _SyntheticOverseasRow("82NVDA", "나스닥 NVDA", "NVDA", "엔비디아", "118.600000", "5", "1.900000", "1.58",
                          "250000000", "29700000", "1.020000", "2910000000", "140.760000", "47.320000"),
)

# Gainer / loser rankings get a consistent direction; other rankings keep the mixed signs.
_SYNTHETIC_SIGNS = {"change_rate_up": "2", "change_rate_down": "5"}


def synthetic_korea_outputs(request: RankingRequest) -> Dict[str, Any]:
    """3 deterministic rows with the live shape (documented in the node guide)."""
    from dataclasses import replace

    rows = list(_SYNTHETIC_KOREA[: min(request.limit, len(_SYNTHETIC_KOREA))])
    sign = _SYNTHETIC_SIGNS.get(request.ranking_type)
    if sign:
        rows = [replace(row, sign=sign) for row in rows]
    return korea_outputs(request, rows)


def synthetic_overseas_outputs(request: RankingRequest) -> Dict[str, Any]:
    from dataclasses import replace

    rows = list(_SYNTHETIC_OVERSEAS[: min(request.limit, len(_SYNTHETIC_OVERSEAS))])
    sign = _SYNTHETIC_SIGNS.get(request.ranking_type)
    if sign:
        rows = [replace(row, sign=sign) for row in rows]
    return overseas_outputs(rows)
