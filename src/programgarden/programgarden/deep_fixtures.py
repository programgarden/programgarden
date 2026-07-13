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


# Number of OHLCV bars every fixture time-series carries. Must comfortably
# exceed the lookback of common indicators (RSI(14), Bollinger(20), SR windows,
# ATR(14), TSMOM(60)) so a deep run computes a *real* (non-None / non-neutral)
# indicator value instead of a "data too short" sentinel — a thin series was the
# Phase 1 source of deep-validate false positives. Capped to keep the single
# deep pass fast (it runs every condition plugin over every symbol within a hard
# 15 s box); a handful of corpus indicators use a longer lookback (e.g. calmar
# 252) and legitimately fall back to a neutral value — that does not break flow.
_FIXTURE_BARS = 64


def _ohlcv_series(symbol: str, *, n: int = _FIXTURE_BARS, base: float = 100.0) -> List[Dict[str, Any]]:
    """Build a deterministic OHLCV series for one symbol (oldest bar first).

    The close path rises for the first ~⅔ of the window then declines into the
    final bar. That gives indicators something non-trivial to chew on (a real RSI
    in the 25–75 band, a real Bollinger position, a real ATR) rather than a
    perfectly monotonic ramp that pins RSI to 0/100. The shape is *deterministic*
    (no randomness) so deep runs stay reproducible.
    """
    bars: List[Dict[str, Any]] = []
    peak = int(n * 0.65)
    price = base
    for i in range(n):
        day = _FIXTURE_ANCHOR + timedelta(days=i)
        # Rise toward the peak, then ease back down — a gentle mean-reverting arc.
        if i <= peak:
            price = base + i * 0.8
        else:
            price = base + peak * 0.8 - (i - peak) * 1.1
        price = max(price, base * 0.5)
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


def _time_series_entries(config: Dict[str, Any], symbols_raw: Any = None) -> List[Dict[str, Any]]:
    """Build the per-symbol ``{symbol, exchange, time_series:[bars]}`` list that
    HistoricalDataNode emits at runtime. Downstream ConditionNode auto-iterates
    this list, so each entry must carry the keys its ``items.extract`` reads
    (``symbol``/``exchange``) plus a ``time_series`` of OHLCV bars.
    """
    syms = _norm_symbols(symbols_raw if symbols_raw is not None else _config_symbols(config))
    entries: List[Dict[str, Any]] = []
    for idx, entry in enumerate(syms):
        entries.append(
            {
                "symbol": entry["symbol"],
                "exchange": entry["exchange"],
                "time_series": _ohlcv_series(entry["symbol"], base=100.0 + idx * 10),
            }
        )
    return entries


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

    Real shape (executor.py ``HistoricalDataNodeExecutor.execute`` return):
    ``{"value": {symbol, exchange, time_series:[bars]} | None,
        "values": [{symbol, exchange, time_series:[bars]}, ...],
        "symbols": [str, ...], "period": str, "interval": str}``.

    Each ``time_series`` bar is ``{date, open, high, low, close, volume}``.
    Downstream ConditionNode auto-iterates ``values`` and reads
    ``item.time_series`` / ``item.symbol``, so this shape must mirror the runtime
    output exactly (the prior ``ohlcv_data`` map shape silently starved the
    ConditionNode and produced deep false positives).
    """
    if symbols_raw is None:
        symbols_raw = config.get("symbol") or _config_symbols(config)
    entries = _time_series_entries(config, symbols_raw)
    single = entries[0] if len(entries) == 1 else None
    return {
        "value": single,
        "values": entries,
        "symbols": [e["symbol"] for e in entries],
        "period": str(config.get("period", "1d")),
        "interval": str(config.get("interval", config.get("period", "1d"))),
    }


def _fixture_balance(currency: str = "USD") -> Dict[str, Any]:
    """Per-currency balance map (RealAccountNode shape) + flat convenience keys.

    Mirrors the real RealAccountNode balance: a currency-keyed map plus a
    ``_summary``. Also carries flat keys (``orderable_amount``, ``total_pnl_rate``)
    that PositionSizingNode / IfNode aggregate checks read directly, so neither
    consumer shape sees a missing field in deep mode.
    """
    return {
        currency: {
            "deposit": 100000.0,
            "orderable_amount": 100000.0,
            "eval_amount": 105000.0,
            "pnl_amount": 5000.0,
            "pnl_rate": 5.0,
        },
        "_summary": {
            "total_deposit": 100000.0,
            "total_eval_amount": 105000.0,
            "total_pnl_amount": 5000.0,
        },
        # Flat convenience keys some consumers (PositionSizing, aggregate IfNode)
        # read directly.
        "cash": 100000.0,
        "total_value": 105000.0,
        "orderable_amount": 100000.0,
        "total_pnl_rate": 5.0,
    }


def _fixture_positions(config: Dict[str, Any], symbols_raw: Any = None) -> List[Dict[str, Any]]:
    """Held positions fixture mirroring the real Account/RealAccount position dict.

    The FIRST position is deliberately *losing* (negative pnl_rate) so per-position
    risk conditions (StopLoss / TrailingStop) trigger during a deep run — a flat
    "everything is +5%" book would never exercise the stop-loss → order → notify
    branch, leaving its ``{{ item.* }}`` bindings unreached (a false negative).
    """
    syms = _norm_symbols(symbols_raw if symbols_raw is not None else _config_symbols(config))
    positions: List[Dict[str, Any]] = []
    for idx, entry in enumerate(syms):
        avg = round(100.0 + idx * 10, 2)
        # First holding is underwater (-8%), the rest are in profit (+5%).
        cur = round(avg * 0.92, 2) if idx == 0 else round(avg * 1.05, 2)
        qty = 10
        positions.append(
            {
                "symbol": entry["symbol"],
                "exchange": entry["exchange"],
                "name": entry["symbol"],
                "qty": qty,
                "quantity": qty,  # NewOrderNode compat key
                "direction": "long",
                "close_side": "sell",
                "avg_price": avg,
                "entry_price": avg,
                "current_price": cur,
                "price": cur,
                "pnl_rate": round((cur - avg) / avg * 100, 2),
                "pnl_amount": round((cur - avg) * qty, 2),
                "eval_amount": round(cur * qty, 2),
                "purchase_amount": round(avg * qty, 2),
                "currency": "USD",
                "market": entry["exchange"],
                "market_code": "82",
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


def futures_contract_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    """FuturesContractNode deep fixture (no o3101 master query).

    Real shape: ``{"symbols": [{exchange, symbol}], "contracts": [...], "count": int}``.

    The month code is derived from the fixture anchor, not the wall clock, so a deep
    run is reproducible. The *symbol string* is therefore not a real listed contract —
    that is fine and deliberate: deep_validate checks field/type/flow integrity, and
    downstream fixtures key off the symbol string only as an opaque identifier.
    """
    raw = config.get("base_products") or []
    if isinstance(raw, str):
        raw = [p.strip() for p in raw.split(",") if p.strip()]
    products = [str(p).strip().upper() for p in raw if str(p).strip()] or ["HMH"]

    # 거래소는 ExchCd 로 정규화한다. config 값을 그대로 되뱉으면, 형제 노드의 enum('6')을
    # 넣은 워크플로우가 게이트를 통과한 뒤 첫 라이브 실행에서만 죽는다 — 게이트의 존재 이유가 없어진다.
    _ENUM_TO_EXCHCD = {"1": "", "2": "CME", "3": "SGX", "4": "EUREX", "5": "ICE", "6": "HKEX", "7": "OSE"}
    exchange = str(config.get("futures_exchange") or "").strip().upper()
    exchange = _ENUM_TO_EXCHCD.get(exchange, exchange) or "HKEX"

    # 월물 문자 코드 (F=1월 … Z=12월) — 실제 노드와 같은 표기를 쓴다.
    # contract_selection 을 실제 노드와 같은 규칙으로 반영한다(front=당월, next=익월,
    # quarterly=3·6·9·12월 중 최근접). fixture 가 이걸 무시하면 세 설정이 같은 심볼을 내
    # 배선 검증이 selection 오류를 못 잡는다.
    month_letters = "FGHJKMNQUVXZ"
    selection = str(config.get("contract_selection") or "front").strip().lower()
    month = _FIXTURE_ANCHOR.month
    if selection == "next":
        month += 1
    elif selection == "quarterly":
        while month % 3:
            month += 1
    year = _FIXTURE_ANCHOR.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    letter = month_letters[month - 1]
    yy = f"{year % 100:02d}"

    contracts: List[Dict[str, Any]] = []
    for product in products:
        contracts.append(
            {
                "symbol": f"{product}{letter}{yy}",
                "exchange": exchange,
                "base_product": product,
                "base_product_name": product,
                "name": f"{product}({year}.{month:02d})",
                "contract_month": f"{year:04d}-{month:02d}",
            }
        )
    return {
        "symbols": [{"exchange": c["exchange"], "symbol": c["symbol"]} for c in contracts],
        "contracts": contracts,
        "count": len(contracts),
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


def _schema_default_value(schema: Any) -> Any:
    """Best-effort default value for one ``output_schema`` entry.

    An entry is either a bare type string (``"number"``) or a JSON-schema-ish
    dict (``{"type": "...", "enum": [...], "items": {...}, "properties": {...}}``)
    — the two shapes ``AIAgentNodeExecutor._build_output_instruction`` /
    ``_validate_structured`` already accept. Returns a type-correct placeholder
    so a downstream ``{{ nodes.<agent>.response.<field> }}`` binding resolves to a
    real value (an enum field resolves to its first allowed value, an object to
    its declared properties, an array to a single shaped element).
    """
    if isinstance(schema, str):
        type_name, spec = schema, {}
    elif isinstance(schema, dict):
        type_name, spec = str(schema.get("type", "string")), schema
    else:
        return "deep_validate"

    enum_vals = spec.get("enum") if isinstance(spec, dict) else None
    if enum_vals:
        return enum_vals[0]

    if type_name in ("string", "str"):
        return "deep_validate"
    if type_name in ("number", "float"):
        return 1.0
    if type_name in ("integer", "int"):
        return 1
    if type_name in ("boolean", "bool"):
        return True
    if type_name == "array":
        items = spec.get("items") if isinstance(spec, dict) else None
        if isinstance(items, (dict, str)):
            return [_schema_default_value(items)]
        return []
    if type_name in ("object", "dict"):
        props = spec.get("properties") if isinstance(spec, dict) else None
        if isinstance(props, dict):
            return {key: _schema_default_value(sub) for key, sub in props.items()}
        return {}
    return "deep_validate"


def ai_agent_fixture(config: Dict[str, Any]) -> Dict[str, Any]:
    """AIAgentNode deep fixture — schema-shaped ``{"response": ...}``, no LLM call.

    A deep run must never hit a live LLM (cost, non-determinism, network) nor
    silently swallow a failed model call. This builds the ``response`` output
    port directly from the node's declared ``output_format`` / ``output_schema``
    so downstream consumers see the same shape they would at runtime:

    - ``"structured"`` + ``output_schema`` → a dict with every declared field
      populated by a type-correct placeholder (enum → first value, nested
      object/array shaped recursively). This is what makes
      ``{{ nodes.<agent>.response.<field> }}`` bindings resolve in deep mode.
    - ``"json"`` → an empty dict (no schema to shape it).
    - ``"text"`` / anything else → a placeholder string.
    """
    output_format = config.get("output_format", "text")
    output_schema = config.get("output_schema")
    if output_format == "structured" and isinstance(output_schema, dict) and output_schema:
        response: Any = {
            key: _schema_default_value(spec) for key, spec in output_schema.items()
        }
    elif output_format == "json":
        response = {}
    else:  # "text" or unknown → raw string
        response = "deep_validate: AIAgentNode response (virtual run, no live LLM call)"
    return {"response": response}


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
