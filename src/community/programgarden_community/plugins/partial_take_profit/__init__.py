"""
PartialTakeProfit (분할 익절) 플러그인

여러 단계에서 분할 매도하여 리스크를 줄이면서 수익 확보.
- levels: [{pnl_pct: 5, sell_pct: 50}, {pnl_pct: 10, sell_pct: 30}, {pnl_pct: 20, sell_pct: 20}]
- strategy_state로 완료된 단계 추적
- 포지션 청산 시 상태 자동 삭제

입력 형식:
- positions: RealAccountNode의 positions 출력 {symbol: {pnl_rate, qty, ...}}
- fields: {levels}
- context: strategy_state 접근용 (선택)
"""

import json
from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features: strategy_state 사용
risk_features: Set[str] = {"state"}

PARTIAL_TAKE_PROFIT_SCHEMA = PluginSchema(
    id="PartialTakeProfit",
    name="Partial Take Profit",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Multi-level partial take profit. Sells portions at different profit levels to lock in gains while maintaining exposure. Tracks completed levels via strategy_state.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "levels": {
            "type": "string",
            "default": '[{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}, {"pnl_pct": 20, "sell_pct": 20}]',
            "title": "Profit Levels (JSON)",
            "description": "JSON array of {pnl_pct, sell_pct} objects. pnl_pct: trigger profit %, sell_pct: portion to sell %",
        },
    },
    required_data=["positions"],
    required_fields=[],
    optional_fields=[],
    tags=["exit", "profit", "partial", "scaling"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "qty": {"type": "int", "description": "Current position quantity"},
        "sell_quantity": {"type": "int", "description": "Quantity to sell at this partial take profit level"},
        "sell_pct": {"type": "float", "description": "Percentage of position to sell (%)"},
        "level_index": {"type": "int", "description": "Index of the triggered profit level"},
        "remaining_levels": {"type": "int", "description": "Number of remaining profit levels not yet triggered"},
        "action": {"type": "str", "description": "Action taken: 'sell', 'hold', 'skip', or 'cleared'"},
    },
    locales={
        "ko": {
            "name": "분할 익절",
            "description": "여러 단계에서 분할 매도하여 리스크를 줄이면서 수익을 확보합니다. 각 단계별 수익률 도달 시 지정 비율만큼 매도합니다.",
            "fields.levels": "익절 단계 (JSON 배열: [{pnl_pct: 수익률%, sell_pct: 매도비율%}])",
        },
    },
)


def _parse_levels(levels_raw: Any) -> List[Dict[str, float]]:
    """levels 파라미터 파싱"""
    if isinstance(levels_raw, list):
        return levels_raw
    if isinstance(levels_raw, str):
        try:
            parsed = json.loads(levels_raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}, {"pnl_pct": 20, "sell_pct": 20}]


async def partial_take_profit_condition(
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """
    분할 익절 조건 평가

    Args:
        positions: {symbol: {pnl_rate, qty, ...}}
        fields: {levels: JSON string or list}
        context: strategy_state 접근용

    Returns:
        passed_symbols, failed_symbols, symbol_results (sell_quantity, sell_pct, level_index 포함)
    """
    if positions is None:
        positions = {}
    if fields is None:
        fields = {}

    levels = _parse_levels(fields.get("levels", None))

    if not positions:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    # strategy_state 접근 헬퍼
    has_state = context and hasattr(context, "risk_tracker") and context.risk_tracker

    async def get_state(key: str) -> Any:
        if has_state:
            return await context.risk_tracker.get_state(key)
        return None

    async def set_state(key: str, value: Any) -> None:
        if has_state:
            await context.risk_tracker.set_state(key, value)

    async def delete_state(key: str) -> None:
        if has_state:
            await context.risk_tracker.delete_state(key)

    passed, failed, symbol_results = [], [], []

    for symbol, pos_data in positions.items():
        pnl_rate = pos_data.get("pnl_rate", 0)
        qty = pos_data.get("qty", pos_data.get("quantity", 0))
        exchange = pos_data.get("market_code", "UNKNOWN")
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(exchange, exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # 수량 0이면 청산 완료 → 상태 삭제
        if qty <= 0:
            await delete_state(f"partial_tp.{symbol}.completed_levels")
            await delete_state(f"partial_tp.{symbol}.original_qty")
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "pnl_rate": round(pnl_rate, 2), "qty": qty,
                "action": "cleared", "reason": "Position closed",
            })
            continue

        # 완료된 단계 로드
        completed_raw = await get_state(f"partial_tp.{symbol}.completed_levels")
        completed_levels = completed_raw if isinstance(completed_raw, list) else []

        original_qty_raw = await get_state(f"partial_tp.{symbol}.original_qty")
        original_qty = original_qty_raw if isinstance(original_qty_raw, (int, float)) and original_qty_raw > 0 else qty

        # 아직 실행 안 된 단계 중 조건 충족하는 것 찾기
        triggered_level = None
        for idx, level in enumerate(levels):
            if idx in completed_levels:
                continue
            if pnl_rate >= level.get("pnl_pct", 0):
                triggered_level = (idx, level)
                break  # 낮은 단계부터 순서대로

        if triggered_level:
            level_idx, level = triggered_level
            sell_pct = level.get("sell_pct", 0)
            sell_quantity = int(original_qty * sell_pct / 100)
            sell_quantity = min(sell_quantity, qty)  # 보유량 초과 방지

            if sell_quantity > 0:
                # 완료 단계 업데이트
                new_completed = completed_levels + [level_idx]
                await set_state(f"partial_tp.{symbol}.completed_levels", new_completed)
                if not completed_levels:
                    await set_state(f"partial_tp.{symbol}.original_qty", qty)

                remaining_levels = len(levels) - len(new_completed)

                passed.append(sym_dict)
                symbol_results.append({
                    "symbol": symbol, "exchange": exchange_name,
                    "pnl_rate": round(pnl_rate, 2), "qty": qty,
                    "sell_quantity": sell_quantity, "sell_pct": sell_pct,
                    "level_index": level_idx, "remaining_levels": remaining_levels,
                    "action": "sell",
                })
            else:
                failed.append(sym_dict)
                symbol_results.append({
                    "symbol": symbol, "exchange": exchange_name,
                    "pnl_rate": round(pnl_rate, 2), "qty": qty,
                    "action": "skip", "reason": "Sell quantity is 0",
                })
        else:
            remaining_levels = len(levels) - len(completed_levels)
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "pnl_rate": round(pnl_rate, 2), "qty": qty,
                "completed_levels": len(completed_levels),
                "remaining_levels": remaining_levels,
                "action": "hold",
            })

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "PartialTakeProfit",
            "levels": levels,
            "total_positions": len(positions),
            "triggered_count": len(passed),
        },
    }


__all__ = ["partial_take_profit_condition", "PARTIAL_TAKE_PROFIT_SCHEMA", "risk_features"]
