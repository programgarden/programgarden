"""
Dynamic Plugin 예제: SimpleBollinger

Bollinger Bands 기반 변동성 돌파/회귀 전략.
중심선(SMA) ± K*표준편차로 상하단 밴드 구성.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleBollinger", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleBollinger",
    name="Simple Bollinger Bands",
    category=PluginCategory.TECHNICAL,
    description="Bollinger Bands 기반 과매수/과매도. 상단 돌파=과매수, 하단 이탈=과매도.",
    fields_schema={
        "period": {"type": "int", "default": 20, "title": "Period"},
        "num_std": {"type": "float", "default": 2.0, "title": "Std Multiplier"},
    },
    required_fields=["symbol", "exchange", "date", "close"],
    tags=["volatility", "bands", "mean-reversion"],
    output_fields={
        "upper_band": {"type": "float", "description": "Upper Bollinger Band"},
        "middle_band": {"type": "float", "description": "Middle Band (SMA)"},
        "lower_band": {"type": "float", "description": "Lower Bollinger Band"},
        "pct_b": {"type": "float", "description": "%B indicator (0=lower, 1=upper)"},
        "signal": {"type": "str", "description": "above_upper / below_lower / inside"},
    },
)


async def simple_bollinger_condition(
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

    period = fields.get("period", 20)
    num_std = fields.get("num_std", 2.0)

    if not data:
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [],
                "values": [], "result": False, "analysis": {"error": "No data"}}

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
        closes = [float(r.get(close_f, 0)) for r in rows if r.get(close_f) is not None]

        if len(closes) < period:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "signal": "insufficient_data"})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        sma = statistics.mean(closes[-period:])
        std = statistics.stdev(closes[-period:])
        upper = round(sma + num_std * std, 4)
        lower = round(sma - num_std * std, 4)
        middle = round(sma, 4)
        last = closes[-1]
        band_width = upper - lower
        pct_b = round((last - lower) / band_width, 4) if band_width > 0 else 0.5

        if last > upper:
            signal = "above_upper"
        elif last < lower:
            signal = "below_lower"
        else:
            signal = "inside"

        triggered = signal != "inside"
        results.append({"symbol": sym, "exchange": exch, "upper_band": upper,
                        "middle_band": middle, "lower_band": lower, "pct_b": pct_b, "signal": signal})
        (passed if triggered else failed).append({"symbol": sym, "exchange": exch})

        ts = []
        for i, r in enumerate(rows):
            s_slice = closes[:i + 1]
            if len(s_slice) >= period:
                m = statistics.mean(s_slice[-period:])
                sd = statistics.stdev(s_slice[-period:])
                ts.append({date_f: r.get(date_f, ""), close_f: r.get(close_f),
                            "upper_band": round(m + num_std * sd, 4),
                            "middle_band": round(m, 4),
                            "lower_band": round(m - num_std * sd, 4)})
            else:
                ts.append({date_f: r.get(date_f, ""), close_f: r.get(close_f)})
        values.append({"symbol": sym, "exchange": exch, "time_series": ts})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleBollinger", "period": period, "num_std": num_std},
    }
