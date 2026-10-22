"""
Dynamic Plugin 예제: SimpleVolumeSpike

거래량 급등 감지. 현재 거래량이 N일 평균의 K배를 초과하면 신호 발생.
가격 변동 방향과 함께 분석하여 의미 있는 거래량 폭증 판별.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleVolumeSpike", "data": "{{ nodes.historical.values }}"}
"""

import statistics
from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleVolumeSpike",
    name="Simple Volume Spike",
    category=PluginCategory.TECHNICAL,
    description="거래량 급등 감지. 현재 거래량이 N일 평균의 K배 초과 시 신호.",
    fields_schema={
        "period": {"type": "int", "default": 20, "title": "Average Period"},
        "multiplier": {"type": "float", "default": 2.0, "title": "Spike Multiplier"},
    },
    required_fields=["symbol", "exchange", "date", "close", "volume"],
    tags=["volume", "spike", "breakout"],
    output_fields={
        "volume_ratio": {"type": "float", "description": "Current volume / average volume"},
        "is_spike": {"type": "bool", "description": "Whether volume spike detected"},
        "price_direction": {"type": "str", "description": "up / down / flat"},
    },
)


async def simple_volume_spike_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    mapping = field_mapping or {}
    close_f = mapping.get("close_field", "close")
    vol_f = mapping.get("volume_field", "volume")
    date_f = mapping.get("date_field", "date")
    sym_f = mapping.get("symbol_field", "symbol")
    exch_f = mapping.get("exchange_field", "exchange")

    period = fields.get("period", 20)
    multiplier = fields.get("multiplier", 2.0)

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

        vols, closes = [], []
        for r in rows:
            try:
                vols.append(float(r.get(vol_f, 0)))
                closes.append(float(r.get(close_f, 0)))
            except (ValueError, TypeError):
                vols.append(0)
                closes.append(0)

        if len(vols) < period + 1:
            failed.append({"symbol": sym, "exchange": exch})
            results.append({"symbol": sym, "exchange": exch, "is_spike": False, "error": "insufficient_data"})
            values.append({"symbol": sym, "exchange": exch, "time_series": []})
            continue

        avg_vol = statistics.mean(vols[-(period + 1):-1])  # 직전 N일 평균
        curr_vol = vols[-1]
        vol_ratio = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 0

        # 가격 방향
        if len(closes) >= 2:
            price_change = closes[-1] - closes[-2]
            price_dir = "up" if price_change > 0 else ("down" if price_change < 0 else "flat")
        else:
            price_dir = "flat"

        is_spike = vol_ratio >= multiplier
        results.append({"symbol": sym, "exchange": exch, "volume_ratio": vol_ratio,
                        "is_spike": is_spike, "price_direction": price_dir})
        (passed if is_spike else failed).append({"symbol": sym, "exchange": exch})
        values.append({"symbol": sym, "exchange": exch, "time_series": []})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleVolumeSpike", "period": period, "multiplier": multiplier},
    }
