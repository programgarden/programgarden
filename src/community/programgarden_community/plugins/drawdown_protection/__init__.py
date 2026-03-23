"""
DrawdownProtection (낙폭 보호) 플러그인

포트폴리오/개별 종목 최대 낙폭 모니터링.
risk_tracker HWM 활용하여 임계 초과 시 전체 청산/절반 축소/신규 주문 중단.

입력 형식:
- positions: RealAccountNode의 positions 출력 {symbol: {pnl_rate, current_price, ...}}
- fields: {max_drawdown_pct, action, recovery_threshold}
"""

from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언
risk_features: Set[str] = {"hwm", "events"}

DRAWDOWN_PROTECTION_SCHEMA = PluginSchema(
    id="DrawdownProtection",
    name="Drawdown Protection",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Monitors portfolio or per-symbol drawdown from peak. Triggers exit or risk reduction when drawdown exceeds threshold.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "max_drawdown_pct": {
            "type": "float",
            "default": -10.0,
            "title": "Max Drawdown (%)",
            "description": "Maximum allowed drawdown percentage (negative value, e.g., -10.0)",
            "ge": -50.0,
            "le": 0.0,
        },
        "action": {
            "type": "string",
            "default": "exit_all",
            "title": "Action",
            "description": "Action when drawdown exceeds threshold",
            "enum": ["exit_all", "reduce_half", "stop_new_orders"],
        },
        "recovery_threshold": {
            "type": "float",
            "default": 5.0,
            "title": "Recovery Threshold (%)",
            "description": "Drawdown recovery percentage to resume trading",
            "ge": 0.0,
            "le": 20.0,
        },
    },
    required_data=["positions"],
    required_fields=[],
    optional_fields=[],
    tags=["drawdown", "risk", "protection", "portfolio"],
    output_fields={
        "drawdown": {"type": "float", "description": "Current drawdown from peak (%)"},
        "max_drawdown_pct": {"type": "float", "description": "Configured maximum allowed drawdown threshold (%)"},
        "triggered": {"type": "bool", "description": "Whether drawdown exceeded the threshold"},
        "action": {"type": "str", "description": "Action taken: 'exit_all', 'reduce_half', 'stop_new_orders', or 'hold'"},
        "current_price": {"type": "float", "description": "Current market price"},
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "hwm_price": {"type": "float", "description": "High-water mark price (available when risk_tracker is active)"},
        "hwm_drawdown_pct": {"type": "float", "description": "Drawdown from HWM tracked by risk_tracker (available when active)"},
    },
    locales={
        "ko": {
            "name": "낙폭 보호 (Drawdown Protection)",
            "description": "포트폴리오 또는 개별 종목의 고점 대비 낙폭을 모니터링합니다. 낙폭이 임계값을 초과하면 전체 청산, 절반 축소, 신규 주문 중단 등의 조치를 취합니다.",
            "fields.max_drawdown_pct": "최대 허용 낙폭 (%, 음수)",
            "fields.action": "조치 (exit_all: 전체 청산, reduce_half: 절반 축소, stop_new_orders: 신규 주문 중단)",
            "fields.recovery_threshold": "거래 재개 기준 회복률 (%)",
        },
    },
)


async def drawdown_protection_condition(
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """낙폭 보호 조건 평가"""
    if positions is None:
        positions = {}
    if fields is None:
        fields = {}

    max_drawdown_pct = fields.get("max_drawdown_pct", -10.0)
    action = fields.get("action", "exit_all")
    recovery_threshold = fields.get("recovery_threshold", 5.0)

    if not positions:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    passed, failed, symbol_results = [], [], []
    has_risk_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker

    for symbol, pos_data in positions.items():
        pnl_rate = pos_data.get("pnl_rate", 0)
        current_price = pos_data.get("current_price", 0)
        exchange = pos_data.get("market_code", "UNKNOWN")

        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(exchange, exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # risk_tracker HWM 기반 drawdown (우선)
        drawdown = pnl_rate  # fallback
        if has_risk_tracker:
            hwm = context.risk_tracker.get_hwm(symbol)
            if hwm and hwm.hwm_price > 0:
                drawdown = -float(hwm.drawdown_pct)  # drawdown_pct는 양수, 여기선 음수로 변환

        triggered = drawdown <= max_drawdown_pct

        result_info = {
            "symbol": symbol, "exchange": exchange_name,
            "drawdown": round(drawdown, 2),
            "max_drawdown_pct": max_drawdown_pct,
            "triggered": triggered,
            "action": action if triggered else "hold",
            "current_price": current_price,
            "pnl_rate": round(pnl_rate, 2),
        }

        if has_risk_tracker:
            hwm = context.risk_tracker.get_hwm(symbol)
            if hwm:
                result_info["hwm_price"] = float(hwm.hwm_price)
                result_info["hwm_drawdown_pct"] = float(hwm.drawdown_pct)

        symbol_results.append(result_info)

        if triggered:
            # action에 따라 sell_quantity 설정
            if action == "reduce_half":
                qty = pos_data.get("qty", 0)
                sym_dict["sell_quantity"] = max(1, int(qty) // 2)
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
            "indicator": "DrawdownProtection",
            "max_drawdown_pct": max_drawdown_pct,
            "action": action,
            "recovery_threshold": recovery_threshold,
            "total_positions": len(positions),
            "triggered_count": len(passed),
        },
    }


__all__ = ["drawdown_protection_condition", "DRAWDOWN_PROTECTION_SCHEMA", "risk_features"]
