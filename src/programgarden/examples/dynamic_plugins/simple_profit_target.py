"""
Dynamic Plugin 예제: SimpleProfitTarget

익절 플러그인. 보유 종목 수익률이 목표에 도달하면 매도 신호 발생.
POSITION 카테고리 — positions 딕셔너리 사용.

워크플로우 사용:
    {"type": "ConditionNode", "plugin": "SimpleProfitTarget",
     "positions": "{{ nodes.account.positions }}"}
"""

from typing import Any, Dict, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

SCHEMA = PluginSchema(
    id="SimpleProfitTarget",
    name="Simple Profit Target",
    category=PluginCategory.POSITION,
    description="보유 종목 수익률이 목표에 도달하면 익절 신호. 예: +10% 수익 시 매도.",
    fields_schema={
        "target_percent": {"type": "float", "default": 10.0, "title": "Target Profit (%)"},
    },
    required_data=["positions"],
    required_fields=[],
    tags=["exit", "profit", "take-profit"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "triggered": {"type": "bool", "description": "Whether profit target was reached"},
    },
)


async def simple_profit_target_condition(
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    if positions is None:
        positions = {}
    if fields is None:
        fields = {}

    target_pct = fields.get("target_percent", 10.0)

    if not positions:
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [],
                "values": [], "result": False, "error": "positions 데이터가 없습니다."}

    passed, failed, results = [], [], []

    for symbol, pos in positions.items():
        pnl_rate = pos.get("pnl_rate", 0)
        exchange = pos.get("exchange", "UNKNOWN")
        sym_dict = {"symbol": symbol, "exchange": exchange}
        triggered = pnl_rate >= target_pct

        results.append({"symbol": symbol, "exchange": exchange,
                        "pnl_rate": round(pnl_rate, 2), "target_percent": target_pct,
                        "triggered": triggered})
        (passed if triggered else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": results, "values": [],
        "result": len(passed) > 0,
        "analysis": {"indicator": "SimpleProfitTarget", "target_percent": target_pct,
                      "total": len(positions), "triggered": len(passed)},
    }
