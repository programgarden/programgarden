"""
Dynamic Plugin 예제: SimpleMACross

이동평균 교차(Golden Cross / Death Cross) 감지.
단기 MA가 장기 MA를 상향 돌파하면 매수, 하향 돌파하면 매도 신호.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleMACross", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleMACross",
    name="Simple MA Cross",
    category=PluginCategory.TECHNICAL,
    description="단기/장기 이동평균 교차 감지. Golden Cross(상향)=매수, Death Cross(하향)=매도.",
    fields_schema={
        "fast_period": {"type": "int", "default": 5, "title": "Fast MA Period"},
        "slow_period": {"type": "int", "default": 20, "title": "Slow MA Period"},
    },
    required_fields=["symbol", "exchange", "date", "close"],
    tags=["trend", "crossover", "moving-average"],
    output_fields={
        "fast_ma": {"type": "float", "description": "Fast moving average value"},
        "slow_ma": {"type": "float", "description": "Slow moving average value"},
        "crossover": {"type": "str", "description": "golden_cross / death_cross / none"},
    },
)


async def simple_ma_cross_condition(
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

    fast_p = fields.get("fast_period", 5)
    slow_p = fields.get("slow_period", 20)

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

        if len(closes) < slow_p + 1:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "crossover": "insufficient_data"})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        sma = lambda v, p: statistics.mean(v[-p:])
        fast_ma = round(sma(closes, fast_p), 4)
        slow_ma = round(sma(closes, slow_p), 4)
        prev_fast = round(sma(closes[:-1], fast_p), 4)
        prev_slow = round(sma(closes[:-1], slow_p), 4)

        crossover = "none"
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            crossover = "golden_cross"
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            crossover = "death_cross"

        triggered = crossover != "none"
        results.append({"symbol": sym, "exchange": exch, "fast_ma": fast_ma,
                        "slow_ma": slow_ma, "crossover": crossover})
        (passed if triggered else failed).append({"symbol": sym, "exchange": exch})
        values.append({"symbol": sym, "exchange": exch, "time_series": []})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleMACross", "fast": fast_p, "slow": slow_p},
    }
