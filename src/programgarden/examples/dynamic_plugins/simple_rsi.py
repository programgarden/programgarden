"""
Dynamic Plugin 예제: SimpleRSI

RSI(Relative Strength Index) 기반 과매수/과매도 판단.
community의 RSI 플러그인과 동일한 출력 형식.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleRSI", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleRSI",
    name="Simple RSI",
    category=PluginCategory.TECHNICAL,
    description="RSI 기반 과매수/과매도 판단. period 기간의 평균 상승/하락으로 RSI 산출.",
    fields_schema={
        "period": {"type": "int", "default": 14, "title": "RSI Period"},
        "overbought": {"type": "float", "default": 70.0, "title": "Overbought Threshold"},
        "oversold": {"type": "float", "default": 30.0, "title": "Oversold Threshold"},
    },
    required_fields=["symbol", "exchange", "date", "close"],
    tags=["momentum", "oscillator", "overbought", "oversold"],
    output_fields={
        "rsi": {"type": "float", "description": "RSI value (0-100)"},
        "signal": {"type": "str", "description": "overbought / oversold / neutral"},
    },
)


def _calc_rsi(closes: List[float], period: int) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = statistics.mean(gains[-period:])
    avg_loss = statistics.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


async def simple_rsi_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    close_f = mapping.get("close_field", "close")
    date_f = mapping.get("date_field", "date")
    sym_f = mapping.get("symbol_field", "symbol")
    exch_f = mapping.get("exchange_field", "exchange")

    period = fields.get("period", 14)
    overbought = fields.get("overbought", 70.0)
    oversold = fields.get("oversold", 30.0)

    if not data:
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [],
                "values": [], "result": False, "analysis": {"error": "No data"}}

    # 종목별 그룹핑
    sym_map: Dict[str, List[Dict]] = {}
    sym_exch: Dict[str, str] = {}
    for row in data:
        s = row.get(sym_f, "")
        if not s:
            continue
        sym_map.setdefault(s, []).append(row)
        sym_exch.setdefault(s, row.get(exch_f, "UNKNOWN"))

    targets = symbols or [{"symbol": s, "exchange": sym_exch.get(s, "UNKNOWN")} for s in sym_map]
    passed, failed, results, values = [], [], [], []

    for t in targets:
        sym = t["symbol"] if isinstance(t, dict) else str(t)
        exch = t.get("exchange", "UNKNOWN") if isinstance(t, dict) else "UNKNOWN"
        rows = sorted(sym_map.get(sym, []), key=lambda x: x.get(date_f, ""))

        closes = []
        for r in rows:
            try:
                closes.append(float(r.get(close_f, 0)))
            except (ValueError, TypeError):
                continue

        rsi = _calc_rsi(closes, period)
        signal = "overbought" if rsi >= overbought else ("oversold" if rsi <= oversold else "neutral")
        triggered = signal != "neutral"

        results.append({"symbol": sym, "exchange": exch, "rsi": rsi, "signal": signal})
        (passed if triggered else failed).append({"symbol": sym, "exchange": exch})

        ts = []
        for i, r in enumerate(rows):
            c_slice = closes[:i + 1]
            v = _calc_rsi(c_slice, period) if len(c_slice) > period else 50.0
            sig = "overbought" if v >= overbought else ("oversold" if v <= oversold else "neutral")
            ts.append({date_f: r.get(date_f, ""), close_f: r.get(close_f), "rsi": v,
                        "signal": sig, "side": "long" if sig == "oversold" else None})
        values.append({"symbol": sym, "exchange": exch, "time_series": ts})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleRSI", "period": period,
                      "overbought": overbought, "oversold": oversold},
    }
