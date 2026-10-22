"""
Dynamic Plugin 예제: SimpleStopLoss

손절 플러그인. 보유 종목의 손실률이 기준을 초과하면 매도 신호 발생.
POSITION 카테고리 — 시계열 데이터 불필요, positions 배열(list[dict]) 사용.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleStopLoss",
     "positions": "{{ nodes.account.positions }}"}
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleStopLoss",
    name="Simple Stop Loss",
    category=PluginCategory.POSITION,
    description="보유 종목 손실률이 기준 초과 시 매도 신호. 예: -3% 손실 시 자동 손절.",
    fields_schema={
        "stop_percent": {"type": "float", "default": -3.0, "title": "Stop Loss (%)"},
    },
    required_data=["positions"],
    required_fields=[],
    tags=["exit", "risk", "stop-loss"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "triggered": {"type": "bool", "description": "Whether stop loss was triggered"},
    },
)


async def simple_stop_loss_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    if fields is None:
        fields = {}

    stop_pct = fields.get("stop_percent", -3.0)

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
        exchange = pos.get("exchange", "UNKNOWN")
        sym_dict = {"symbol": symbol, "exchange": exchange}
        triggered = pnl_rate <= stop_pct

        results.append({"symbol": symbol, "exchange": exchange,
                        "pnl_rate": round(pnl_rate, 2), "stop_percent": stop_pct,
                        "triggered": triggered})
        (passed if triggered else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": [],
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleStopLoss", "stop_percent": stop_pct,
                      "total": len(positions), "triggered": len(passed)},
    }
