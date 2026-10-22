"""
Dynamic Plugin 예제: SimpleDoji

도지(Doji) 캔들 패턴 감지. 시가≈종가인 십자형 캔들로 추세 전환 경고.
standard, long_legged, dragonfly, gravestone 4가지 유형 분류.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleDoji", "data": "{{ nodes.historical.values }}"}
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleDoji",
    name="Simple Doji",
    category=PluginCategory.TECHNICAL,
    description="도지 캔들 패턴 감지. 시가와 종가가 거의 같은 십자형 캔들로 추세 전환 경고.",
    fields_schema={
        "body_threshold": {"type": "float", "default": 0.1, "title": "Body Threshold",
                           "description": "몸통/전체범위 비율 기준 (10%)"},
    },
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    tags=["candlestick", "pattern", "doji", "reversal"],
    output_fields={
        "pattern_detected": {"type": "bool", "description": "Whether doji pattern detected"},
        "doji_type": {"type": "str", "description": "standard / long_legged / dragonfly / gravestone"},
        "body_ratio": {"type": "float", "description": "Body-to-range ratio"},
    },
)


def _classify_doji(o: float, h: float, l: float, c: float, threshold: float) -> Dict[str, Any]:
    total_range = h - l
    if total_range <= 0:
        return {"detected": False, "doji_type": None, "body_ratio": 0}

    body_ratio = abs(c - o) / total_range
    if body_ratio > threshold:
        return {"detected": False, "doji_type": None, "body_ratio": round(body_ratio, 4)}

    upper = (h - max(o, c)) / total_range
    lower = (min(o, c) - l) / total_range

    if lower > 0.4 and upper < 0.15:
        doji_type = "dragonfly"
    elif upper > 0.4 and lower < 0.15:
        doji_type = "gravestone"
    elif upper > 0.35 and lower > 0.35:
        doji_type = "long_legged"
    else:
        doji_type = "standard"

    return {"detected": True, "doji_type": doji_type, "body_ratio": round(body_ratio, 4)}


async def simple_doji_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    open_f = mapping.get("open_field", "open")
    high_f = mapping.get("high_field", "high")
    low_f = mapping.get("low_field", "low")
    close_f = mapping.get("close_field", "close")
    date_f = mapping.get("date_field", "date")
    sym_f = mapping.get("symbol_field", "symbol")
    exch_f = mapping.get("exchange_field", "exchange")

    threshold = fields.get("body_threshold", 0.1)

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

        if not rows:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "pattern_detected": False})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        last = rows[-1]
        try:
            o = float(last.get(open_f, 0))
            h = float(last.get(high_f, 0))
            l = float(last.get(low_f, 0))
            c = float(last.get(close_f, 0))
        except (ValueError, TypeError):
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "pattern_detected": False})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        result = _classify_doji(o, h, l, c, threshold)
        results.append({"symbol": sym, "exchange": exch, "pattern_detected": result["detected"],
                        "doji_type": result["doji_type"], "body_ratio": result["body_ratio"]})
        (passed if result["detected"] else failed).append({"symbol": sym, "exchange": exch})
        values.append({"symbol": sym, "exchange": exch, "time_series": []})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleDoji", "body_threshold": threshold},
    }
