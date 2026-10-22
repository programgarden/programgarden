"""
Dynamic Plugin 예제: SimpleATR

ATR(Average True Range) 변동성 지표.
True Range의 N일 평균으로 변동성 측정. 고변동성 구간 필터링에 활용.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleATR", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleATR",
    name="Simple ATR",
    category=PluginCategory.TECHNICAL,
    description="ATR 변동성 지표. True Range N일 평균으로 변동성 측정.",
    fields_schema={
        "period": {"type": "int", "default": 14, "title": "ATR Period"},
        "threshold_pct": {"type": "float", "default": 3.0, "title": "Threshold %",
                          "description": "ATR/종가 비율이 이 값 이상이면 고변동성 판단"},
    },
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    tags=["volatility", "atr", "risk"],
    output_fields={
        "atr": {"type": "float", "description": "Average True Range value"},
        "atr_pct": {"type": "float", "description": "ATR as percentage of close price"},
        "is_high_volatility": {"type": "bool", "description": "Whether ATR% exceeds threshold"},
    },
)


async def simple_atr_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    high_f = mapping.get("high_field", "high")
    low_f = mapping.get("low_field", "low")
    close_f = mapping.get("close_field", "close")
    date_f = mapping.get("date_field", "date")
    sym_f = mapping.get("symbol_field", "symbol")
    exch_f = mapping.get("exchange_field", "exchange")

    period = fields.get("period", 14)
    threshold_pct = fields.get("threshold_pct", 3.0)

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

        if len(rows) < period + 1:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "atr": 0, "is_high_volatility": False,
                            "error": "insufficient_data"})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        # True Range 계산
        true_ranges = []
        for i in range(1, len(rows)):
            try:
                h = float(rows[i].get(high_f, 0))
                l = float(rows[i].get(low_f, 0))
                prev_c = float(rows[i - 1].get(close_f, 0))
            except (ValueError, TypeError):
                true_ranges.append(0)
                continue
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            true_ranges.append(tr)

        atr = round(statistics.mean(true_ranges[-period:]), 4)
        last_close = float(rows[-1].get(close_f, 1))
        atr_pct = round((atr / last_close) * 100, 2) if last_close > 0 else 0
        is_high = atr_pct >= threshold_pct

        results.append({"symbol": sym, "exchange": exch, "atr": atr,
                        "atr_pct": atr_pct, "is_high_volatility": is_high})
        (passed if is_high else failed).append({"symbol": sym, "exchange": exch})
        values.append({"symbol": sym, "exchange": exch, "time_series": []})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleATR", "period": period, "threshold_pct": threshold_pct},
    }
