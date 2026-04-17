"""
Dynamic Plugin 예제: SimpleTrailingStop

추적 손절(Trailing Stop) 플러그인.
고점 대비 하락폭이 trail_percent를 초과하면 매도 신호.
POSITION 카테고리 — positions 배열(list[dict]) 사용.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleTrailingStop",
     "positions": "{{ nodes.account.positions }}"}
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleTrailingStop",
    name="Simple Trailing Stop",
    category=PluginCategory.POSITION,
    description="고점 대비 하락폭이 기준 초과 시 매도. 수익 구간에서 이익 보호.",
    fields_schema={
        "trail_percent": {"type": "float", "default": 5.0, "title": "Trail (%)"},
    },
    required_data=["positions"],
    required_fields=[],
    tags=["exit", "trailing", "risk"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "high_pnl_rate": {"type": "float", "description": "Highest P&L rate reached"},
        "drawdown_from_high": {"type": "float", "description": "Drawdown from high (%)"},
        "triggered": {"type": "bool", "description": "Whether trailing stop was triggered"},
    },
)


async def simple_trailing_stop_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    if fields is None:
        fields = {}

    trail_pct = fields.get("trail_percent", 5.0)

    positions = positions or []
    if not positions:
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [],
                "values": [], "result": False, "error": "positions 데이터가 없습니다."}

    passed, failed, results = [], [], []

    for pos in positions:
        symbol = pos.get("symbol")
        if not symbol:
            continue
        pnl_rate = pos.get("pnl_rate", 0)
        # high_pnl_rate는 RealAccountNode가 추적하는 최고 수익률
        # 없으면 현재 pnl_rate를 고점으로 가정
        high_pnl = pos.get("high_pnl_rate", max(pnl_rate, 0))
        exchange = pos.get("exchange", "UNKNOWN")
        sym_dict = {"symbol": symbol, "exchange": exchange}

        # 고점 대비 하락폭
        drawdown = high_pnl - pnl_rate
        triggered = drawdown >= trail_pct and high_pnl > 0  # 수익 구간에서만 작동

        results.append({
            "symbol": symbol, "exchange": exchange,
            "pnl_rate": round(pnl_rate, 2),
            "high_pnl_rate": round(high_pnl, 2),
            "drawdown_from_high": round(drawdown, 2),
            "trail_percent": trail_pct,
            "triggered": triggered,
        })
        (passed if triggered else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": [],
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleTrailingStop", "trail_percent": trail_pct,
                      "total": len(positions), "triggered": len(passed)},
    }
