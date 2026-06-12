"""Deep-validate fixture generators (virtual full-execution).

`deep_validate` runs a workflow once, end-to-end, without touching the broker
network or placing any real order. Realtime / data-fetch nodes that would
normally wait for live events or hit the LS API instead return a *fixture* — a
schema-shaped default payload — so the flow keeps flowing to downstream nodes
and field/type/flow integrity can be checked.

Every generator here is pure and synchronous: it derives a reasonable default
from the node config (mostly the requested symbols), never performs I/O, and
matches the node's real output port shape so downstream consumers see the same
keys they would at runtime.

Callers may override any fixture via
``context_params={"deep_fixtures": {node_id_or_type: {...}}}``; that override is
applied by the executor (``context.get_deep_fixture``) *before* falling back to
these defaults.

All user-facing strings in this module must be English.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# A single deterministic "as-of" date for fixture time series, so deep runs are
# reproducible and do not depend on wall-clock during a validation pass.
_FIXTURE_ANCHOR = datetime(2025, 1, 2, tzinfo=timezone.utc)


def _norm_symbols(raw: Any) -> List[Dict[str, str]]:
    """Normalise a symbols input into ``[{"symbol", "exchange"}]``.

    Accepts the shapes the executors accept: a list of strings, a list of
    ``{"symbol", "exchange"}`` dicts, or a single such dict. Returns at least one
    entry (a placeholder) so a fixture is always non-empty — an empty list would
    let an unrelated "no symbols" error mask the integrity check.
    """
    out: List[Dict[str, str]] = []
    if isinstance(raw, dict):
        raw = [raw]
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                sym = str(entry.get("symbol", "") or "").strip()
                exch = str(entry.get("exchange", "") or "").strip()
                if sym:
                    out.append({"symbol": sym, "exchange": exch or "NASDAQ"})
            elif isinstance(entry, str) and entry.strip():
                out.append({"symbol": entry.strip(), "exchange": "NASDAQ"})
    if not out:
        out.append({"symbol": "AAPL", "exchange": "NASDAQ"})
    return out


def _config_symbols(config: Dict[str, Any]) -> Any:
    """Best-effort symbols extraction from a node config (no context I/O)."""
    for key in ("symbols", "symbol"):
        if config.get(key):
            return config[key]
    return None


def _ohlcv_series(symbol: str, *, n: int = 5, base: float = 100.0) -> List[Dict[str, Any]]:
    """Build a small deterministic OHLCV series for one symbol."""
    bars: List[Dict[str, Any]] = []
    for i in range(n):
        day = _FIXTURE_ANCHOR + timedelta(days=i)
        price = base + i
        bars.append(
            {
                "date": day.strftime("%Y%m%d"),
                "open": round(price - 0.5, 2),
                "high": round(price + 1.0, 2),
                "low": round(price - 1.0, 2),
                "close": round(price, 2),
                "volume": 1_000_000 + i * 1000,
            }
        )
    return bars


def real_market_data_fixture(config: Dict[str, Any], symbols_raw: Any = None) -> Dict[str, Any]:
    """RealMarketDataNode deep fixture.

    Real shape: ``{"symbols", "ohlcv_data": {SYM: [bars]}, "data": {SYM: [bars]}}``.
    """
    syms = _norm_symbols(symbols_raw if symbols_raw is not None else _config_symbols(config))
    ohlcv: Dict[str, List[Dict[str, Any]]] = {}
    for idx, entry in enumerate(syms):
        ohlcv[entry["symbol"]] = _ohlcv_series(entry["symbol"], base=100.0 + idx * 10)
    return {
        "symbols": syms,
        "ohlcv_data": ohlcv,
        "data": dict(ohlcv),
    }


def market_data_fixture(config: Dict[str, Any], symbols_raw: Any = None) -> Dict[str, Any]:
    """MarketDataNode (REST current-price) deep fixture.

    Real shape: ``{"values": [{symbol, exchange, price, change, change_pct,
    volume, open, high, low, close, per, eps}]}``.
    """
    syms = _norm_symbols(symbols_raw if symbols_raw is not None else _config_symbols(config))
    values: List[Dict[str, Any]] = []
    for idx, entry in enumerate(syms):
        price = round(100.0 + idx * 10, 2)
        values.append(
            {
                "symbol": entry["symbol"],
                "exchange": entry["exchange"],
                "price": price,
                "change": 1.0,
                "change_pct": 1.0,
                "volume": 1_000_000,
                "open": round(price - 0.5, 2),
                "high": round(price + 1.0, 2),
                "low": round(price - 1.0, 2),
                "close": price,
                "per": 15.0,
                "eps": 5.0,
            }
        )
    return {"values": values}


def historical_data_fixture(config: Dict[str, Any], symbols_raw: Any = None) -> Dict[str, Any]:
    """HistoricalDataNode deep fixture.

    Real shape: ``{"ohlcv_data": {SYM: [bars]}, "symbols": [...]}``. The historical
    node takes a single ``symbol`` (item-based); fall back to that, then symbols.
    """
    if symbols_raw is None:
        symbols_raw = config.get("symbol") or _config_symbols(config)
    syms = _norm_symbols(symbols_raw)
    ohlcv: Dict[str, List[Dict[str, Any]]] = {}
    for idx, entry in enumerate(syms):
        ohlcv[entry["symbol"]] = _ohlcv_series(entry["symbol"], n=20, base=100.0 + idx * 10)
    return {
        "ohlcv_data": ohlcv,
        "symbols": [s["symbol"] for s in syms],
    }


def _fixture_balance(currency: str = "USD") -> Dict[str, Any]:
    return {
        currency: {
            "deposit": 100000.0,
            "orderable_amount": 100000.0,
            "eval_amount": 105000.0,
            "pnl_amount": 5000.0,
            "pnl_rate": 5.0,
        },
        # Flat convenience keys some consumers read directly.
        "cash": 100000.0,
        "total_value": 105000.0,
        "orderable_amount": 100000.0,
    }


def _fixture_positions(config: Dict[str, Any], symbols_raw: Any = None) -> List[Dict[str, Any]]:
    syms = _norm_symbols(symbols_raw if symbols_raw is not None else _config_symbols(config))
    positions: List[Dict[str, Any]] = []
    for idx, entry in enumerate(syms):
        avg = round(100.0 + idx * 10, 2)
        cur = round(avg + 5.0, 2)
        positions.append(
            {
                "symbol": entry["symbol"],
                "exchange": entry["exchange"],
                "qty": 10,
                "avg_price": avg,
                "current_price": cur,
                "pnl_rate": round((cur - avg) / avg * 100, 2),
                "pnl_amount": round((cur - avg) * 10, 2),
                "currency": "USD",
            }
        )
    return positions


def real_account_fixture(config: Dict[str, Any], symbols_raw: Any = None) -> Dict[str, Any]:
    """RealAccountNode deep fixture.

    Real shape: ``{"positions": [...], "balance": {...}, "open_orders": {}}``.
    """
    return {
        "positions": _fixture_positions(config, symbols_raw),
        "balance": _fixture_balance(),
        "open_orders": {},
    }


def account_fixture(config: Dict[str, Any], symbols_raw: Any = None) -> Dict[str, Any]:
    """AccountNode (REST) deep fixture.

    Real shape: ``{"positions": [...], "balance": {...}}``.
    """
    return {
        "positions": _fixture_positions(config, symbols_raw),
        "balance": _fixture_balance(),
    }


def open_orders_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    """OpenOrdersNode deep fixture (no pending orders — real LS query blocked).

    Real shape: ``{"open_orders": [...], "count": N}``.
    """
    return {"open_orders": [], "count": 0}


def real_order_event_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    """RealOrderEventNode deep fixture (one simulated fill).

    Real shape includes a ``filled`` payload + ``status`` field.
    """
    ts = _FIXTURE_ANCHOR.isoformat()
    return {
        "status": "체결",
        "filled": {
            "timestamp": ts,
            "symbol": "AAPL",
            "order_no": "DEEP-0001",
            "side": "buy",
            "order_qty": 10,
            "order_price": 100.0,
            "status": "체결",
        },
    }


def market_status_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    """MarketStatusNode deep fixture (markets open).

    Real shape: ``{"statuses": [{market, status}]}``.
    """
    return {
        "statuses": [
            {"market": "NASDAQ", "status": "OPEN"},
            {"market": "NYSE", "status": "OPEN"},
        ],
    }


def broker_connection_fixture(
    node_type: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """BrokerNode deep fixture connection (no LS login, no fill-price sync).

    Mirrors the real success shape ``{"connected": True, "connection": {...}}``
    so downstream nodes that read ``connection`` (broker auto-injection) keep
    flowing. Credentials are placeholders — every downstream broker-bound node is
    itself short-circuited in deep mode, so they are never used for a real call.
    """
    if "Futures" in node_type:
        product = "overseas_futures"
    elif "Korea" in node_type:
        product = "korea_stock"
    else:
        product = config.get("product", "overseas_stock")
    paper_trading = bool(config.get("paper_trading", False)) if product != "korea_stock" else False
    return {
        "connected": True,
        "connection": {
            "provider": config.get("provider", "ls-sec.co.kr"),
            "product": product,
            "paper_trading": paper_trading,
            "appkey": "DEEP_VALIDATE_APPKEY",
            "appsecret": "DEEP_VALIDATE_APPSECRET",
        },
    }


def apply_override(default: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Shallow-merge a caller override on top of a default fixture.

    Override keys win; unspecified keys keep the schema-shaped default so the
    flow still has every output port populated.
    """
    if not override:
        return default
    merged = dict(default)
    merged.update(override)
    return merged
