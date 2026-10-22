"""Listing exchange of the overseas-futures contracts an account reports.

CIDBQ01500 (open positions) and CIDBQ02400 (pending orders) name a contract
but carry no exchange or market field. The exchange code is read from o3105
``ExchCd``, the contract-detail TR that FuturesContractInfoNode already uses,
under the same identity rules as ``futures_contract_info.read_contract_info``:
HTTP 200, no error, ``rsp_cd`` 00000, an echoed ``Symbol`` equal to the
requested contract and a non-empty ``ExchCd``. Anything else leaves the
exchange unknown (``None``). No default exchange is ever substituted.

Each execution context (one workflow run) remembers only confirmed answers: a
contract whose exchange o3105 confirmed is never read again in that run. An
unresolved read is not cached as an answer. A later node execution in the same
run reads that contract again, at most once per ``RETRY_UNRESOLVED_SECONDS``
(5 minutes) per contract, so a transient failure does not leave a long-running
workflow without the exchange until it is restarted. Reads are serialized and
spaced like the startup broker reads so the shared app key is not burst.
Request fields follow ``finance/example/overseas_futureoption/run_o3105.py``
(symbol only).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Iterable, Optional

# Same gap the startup broker reads keep between consecutive TRs on one app key
# (database/broker_snapshot.py). o3105 is limited to 2 requests per second.
READ_SPACING_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 20.0
# Minimum time between two o3105 reads of a contract whose exchange is still
# unresolved (measured between the starts of the reads, per contract).
RETRY_UNRESOLVED_SECONDS = 300.0
SOURCE_TR = "o3105"

_sleep = asyncio.sleep
_monotonic = time.monotonic


class _RunExchangeCache:
    """Per-run o3105 state.

    ``exchanges`` holds confirmed answers only. ``unresolved_at`` holds, per
    contract still without an answer, the monotonic start time of its last read.
    """

    __slots__ = ("exchanges", "unresolved_at", "lock")

    def __init__(self) -> None:
        self.exchanges: Dict[str, str] = {}
        self.unresolved_at: Dict[str, float] = {}
        self.lock = asyncio.Lock()


def _run_cache(context: Any) -> _RunExchangeCache:
    cache = getattr(context, "_futures_exchange_cache", None)
    if not isinstance(cache, _RunExchangeCache):
        cache = _RunExchangeCache()
        setattr(context, "_futures_exchange_cache", cache)
    return cache


def exchange_from_contract_detail(response: Any, symbol: str) -> Optional[str]:
    """Return o3105 ``ExchCd`` for ``symbol``, or ``None`` without exact evidence."""
    if (
        getattr(response, "status_code", None) != 200
        or getattr(response, "error_msg", None)
        or getattr(response, "rsp_cd", None) != "00000"
    ):
        return None
    block = getattr(response, "block", None)
    fields = getattr(block, "model_fields_set", None)
    if block is None or not isinstance(fields, (set, frozenset)) or not {"Symbol", "ExchCd"} <= fields:
        return None
    echoed, exchange = getattr(block, "Symbol", None), getattr(block, "ExchCd", None)
    if not isinstance(echoed, str) or echoed.strip() != symbol or not isinstance(exchange, str):
        return None
    return exchange.strip() or None


async def _read_exchange(ls: Any, symbol: str) -> Optional[str]:
    from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105InBlock

    try:
        response = await asyncio.wait_for(
            ls.overseas_futureoption().market().o3105(body=O3105InBlock(symbol=symbol)).req_async(),
            timeout=READ_TIMEOUT_SECONDS,
        )
    except Exception:  # noqa: BLE001 - an unavailable read leaves the exchange unknown
        return None
    return exchange_from_contract_detail(response, symbol)


async def resolve_contract_exchanges(
    ls: Any, symbols: Iterable[str], context: Any, node_id: str,
) -> Dict[str, Optional[str]]:
    """Map each distinct contract symbol to its o3105 exchange code or ``None``.

    A confirmed exchange is reused for the rest of the run. An unresolved
    contract is read again only when ``RETRY_UNRESOLVED_SECONDS`` have passed
    since its last read started; until then it stays ``None`` without a read.
    """
    wanted = [symbol for symbol in dict.fromkeys(symbols) if isinstance(symbol, str) and symbol]
    if not wanted:
        return {}
    cache = _run_cache(context)
    async with cache.lock:
        for symbol in wanted:
            if symbol in cache.exchanges:
                continue
            last_read = cache.unresolved_at.get(symbol)
            if last_read is not None:
                wait = RETRY_UNRESOLVED_SECONDS - (_monotonic() - last_read)
                if wait > 0:
                    context.log(
                        "debug",
                        f"Futures exchange for {symbol} is still unavailable; the next {SOURCE_TR} "
                        f"read is allowed in {int(wait) + 1} s",
                        node_id,
                    )
                    continue
            await _sleep(READ_SPACING_SECONDS)
            started = _monotonic()
            exchange = await _read_exchange(ls, symbol)
            if exchange is not None:
                cache.exchanges[symbol] = exchange
                cache.unresolved_at.pop(symbol, None)
                continue
            cache.unresolved_at[symbol] = started
            context.log(
                "warning",
                f"Futures exchange for {symbol} is unavailable ({SOURCE_TR} gave no matching "
                f"exchange code); the row's exchange is left empty and {SOURCE_TR} is read again "
                f"on a later node execution after {int(RETRY_UNRESOLVED_SECONDS // 60)} minutes",
                node_id,
            )
        return {symbol: cache.exchanges.get(symbol) for symbol in wanted}
