"""
TimeBasedExit (시간 기반 청산) 플러그인

보유 기간이 설정된 일수를 초과하면 자동 청산 시그널 발생.
- strategy_state에 진입일 저장
- 포지션 청산 시 상태 자동 삭제
- 포지션이 사라진 종목의 상태도 자동 정리

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "qty": 100, ...}, ...]
- fields: {max_hold_days, warn_days}
- context: strategy_state 접근용 (선택)
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features: strategy_state 사용
risk_features: Set[str] = {"state"}

TIME_BASED_EXIT_SCHEMA = PluginSchema(
    id="TimeBasedExit",
    name="Time-based Exit",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Generates exit signal when holding period exceeds configured days. Tracks entry date via strategy_state. Auto-cleans state for closed positions.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "max_hold_days": {
            "type": "int",
            "default": 5,
            "title": "Max Hold Days",
            "description": "Maximum holding days before exit signal",
            "ge": 1,
            "le": 365,
        },
        "warn_days": {
            "type": "int",
            "default": 0,
            "title": "Warn Days",
            "description": "Days before max to start warning (0 = disabled)",
            "ge": 0,
            "le": 365,
        },
    },
    required_data=["positions"],
    required_fields=[],
    optional_fields=[],
    tags=["exit", "time", "holding_period"],
    output_fields={
        "entry_date": {"type": "str", "description": "Detected entry date (YYYY-MM-DD)"},
        "hold_days": {"type": "int", "description": "Number of days position has been held"},
        "max_hold_days": {"type": "int", "description": "Maximum allowed holding days"},
        "warn": {"type": "bool", "description": "Whether the warning threshold has been crossed"},
        "action": {"type": "str", "description": "Recommended action: 'exit', 'warn', 'hold', or 'cleared'"},
    },
    locales={
        "ko": {
            "name": "시간 기반 청산",
            "description": "보유 기간이 설정된 일수를 초과하면 자동으로 청산 시그널을 발생시킵니다. 진입일을 자동으로 추적합니다.",
            "fields.max_hold_days": "최대 보유 일수",
            "fields.warn_days": "경고 시작 일수 (0 = 비활성)",
        },
    },
)


async def time_based_exit_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """
    시간 기반 청산 조건 평가

    Args:
        positions: RealAccountNode의 positions 출력 (list[dict])
                   [{"symbol": "AAPL", "qty": 100, ...}, ...]
        fields: {max_hold_days, warn_days}
        context: strategy_state 접근용
    """
    if fields is None:
        fields = {}

    max_hold_days = fields.get("max_hold_days", 5)
    warn_days = fields.get("warn_days", 0)

    positions = positions or []
    if not positions:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

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

    today = date.today()
    today_str = today.isoformat()

    passed, failed, symbol_results = [], [], []

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        qty = pos_data.get("qty", pos_data.get("quantity", 0))
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # 수량 0이면 청산 완료 → 상태 삭제
        if qty <= 0:
            await delete_state(f"time_exit.{symbol}.entry_date")
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "action": "cleared", "reason": "Position closed",
            })
            continue

        # 진입일 로드 또는 최초 감지
        entry_date_str = await get_state(f"time_exit.{symbol}.entry_date")
        if not entry_date_str:
            entry_date_str = today_str
            await set_state(f"time_exit.{symbol}.entry_date", entry_date_str)

        try:
            entry_date = date.fromisoformat(entry_date_str)
        except (ValueError, TypeError):
            entry_date = today
            await set_state(f"time_exit.{symbol}.entry_date", today_str)

        hold_days = (today - entry_date).days
        is_warn = warn_days > 0 and hold_days >= (max_hold_days - warn_days) and hold_days < max_hold_days
        is_exit = hold_days >= max_hold_days

        symbol_results.append({
            "symbol": symbol, "exchange": exchange_name,
            "entry_date": entry_date_str,
            "hold_days": hold_days,
            "max_hold_days": max_hold_days,
            "warn": is_warn,
            "action": "exit" if is_exit else ("warn" if is_warn else "hold"),
        })

        if is_exit:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "TimeBasedExit",
            "max_hold_days": max_hold_days,
            "warn_days": warn_days,
            "total_positions": len(positions),
            "exit_count": len(passed),
        },
    }


__all__ = ["time_based_exit_condition", "TIME_BASED_EXIT_SCHEMA", "risk_features"]
