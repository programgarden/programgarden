"""
Dynamic Plugin 예제: SimpleMACD

MACD(Moving Average Convergence Divergence) 추세 추종 지표.
MACD 라인과 시그널 라인의 교차로 매매 신호 생성.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleMACD", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleMACD",
    name="Simple MACD",
    category=PluginCategory.TECHNICAL,
    description="MACD 라인과 시그널 라인 교차로 추세 전환 감지. EMA 대신 SMA로 간소화.",
    fields_schema={
        "fast_period": {"type": "int", "default": 12, "title": "Fast Period"},
        "slow_period": {"type": "int", "default": 26, "title": "Slow Period"},
        "signal_period": {"type": "int", "default": 9, "title": "Signal Period"},
    },
    required_fields=["symbol", "exchange", "date", "close"],
    tags=["trend", "momentum", "crossover"],
    output_fields={
        "macd": {"type": "float", "description": "MACD line (fast MA - slow MA)"},
        "signal_line": {"type": "float", "description": "Signal line (MA of MACD)"},
        "histogram": {"type": "float", "description": "MACD - Signal"},
        "crossover": {"type": "str", "description": "bullish_cross / bearish_cross / none"},
    },
)


def _sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return statistics.mean(values[-period:])


def _calc_macd_series(closes: List[float], fast: int, slow: int, signal: int):
    """전체 시계열에서 MACD 계산"""
    macd_vals = []
    for i in range(len(closes)):
        s = closes[:i + 1]
        if len(s) >= slow:
            macd_vals.append(_sma(s, fast) - _sma(s, slow))
        else:
            macd_vals.append(0.0)
    signal_vals = []
    for i in range(len(macd_vals)):
        s = macd_vals[:i + 1]
        signal_vals.append(_sma(s, signal) if len(s) >= signal else 0.0)
    return macd_vals, signal_vals


async def simple_macd_condition(
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

    fast = fields.get("fast_period", 12)
    slow = fields.get("slow_period", 26)
    sig_p = fields.get("signal_period", 9)

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

        if len(closes) < slow:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "macd": 0, "signal_line": 0,
                            "histogram": 0, "crossover": "insufficient_data"})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        macd_vals, sig_vals = _calc_macd_series(closes, fast, slow, sig_p)
        macd = round(macd_vals[-1], 4)
        sig_line = round(sig_vals[-1], 4)
        hist = round(macd - sig_line, 4)

        # 교차 판단
        crossover = "none"
        if len(macd_vals) >= 2 and len(sig_vals) >= 2:
            prev_diff = macd_vals[-2] - sig_vals[-2]
            curr_diff = macd_vals[-1] - sig_vals[-1]
            if prev_diff <= 0 and curr_diff > 0:
                crossover = "bullish_cross"
            elif prev_diff >= 0 and curr_diff < 0:
                crossover = "bearish_cross"

        triggered = crossover != "none"
        results.append({"symbol": sym, "exchange": exch, "macd": macd,
                        "signal_line": sig_line, "histogram": hist, "crossover": crossover})
        (passed if triggered else failed).append({"symbol": sym, "exchange": exch})

        ts = []
        for i, r in enumerate(rows):
            m = round(macd_vals[i], 4) if i < len(macd_vals) else 0
            s_v = round(sig_vals[i], 4) if i < len(sig_vals) else 0
            ts.append({date_f: r.get(date_f, ""), close_f: r.get(close_f),
                        "macd": m, "signal_line": s_v, "histogram": round(m - s_v, 4)})
        values.append({"symbol": sym, "exchange": exch, "time_series": ts})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleMACD", "fast": fast, "slow": slow, "signal": sig_p},
    }
