"""
DrawdownProtection (낙폭 보호) 플러그인

포트폴리오/개별 종목 최대 낙폭 모니터링.
risk_tracker HWM 활용하여 임계 초과 시 전체 청산/절반 축소/신규 주문 중단.

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "pnl_rate": -5.2, "current_price": 150.0, ...}, ...]
- fields: {max_drawdown_pct, action, recovery_threshold}
"""

from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import below_broker_lot, coerce_number, half_position_qty


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
        "action": {"type": "str", "description": "Action taken: 'exit_all', 'reduce_half', 'stop_new_orders', 'hold', or 'skip' (drawdown could not be determined because pnl_rate was unreadable and no HWM was available)"},
        "reason": {"type": "str", "description": "Why the position was skipped: names the unreadable field and its raw value (present on the 'skip' action)"},
        "current_price": {"type": "float", "description": "Current market price (absent when it could not be read; see current_price_unavailable_reason)"},
        "current_price_unavailable_reason": {"type": "str", "description": "Present when the position's current_price could not be read as a number (display only)"},
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%) (absent when it could not be read; see pnl_rate_unavailable_reason)"},
        "pnl_rate_unavailable_reason": {"type": "str", "description": "Present when pnl_rate could not be read but the drawdown was still determined from the risk_tracker HWM"},
        "hwm_price": {"type": "float", "description": "High-water mark price (available when risk_tracker is active)"},
        "hwm_drawdown_pct": {"type": "float", "description": "Drawdown from HWM tracked by risk_tracker (available when active)"},
        "sell_quantity": {"type": "float", "description": "Quantity to sell for the 'reduce_half' action: exactly half of the held quantity, never rounded up and never above the held quantity (fractional halves are kept; the order node truncates to the broker lot and reports the remainder)"},
        "sell_quantity_unavailable_reason": {"type": "str", "description": "Present only when 'reduce_half' triggered but the held quantity could not be read, so no sell quantity was emitted"},
        "reduce_skipped_reason": {"type": "str", "description": "Present when the 'reduce_half' quantity is below 1 share: the order node truncates to the integer part (0) and builds no order, so the reduction silently does nothing this round"},
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
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """낙폭 보호 조건 평가"""
    if fields is None:
        fields = {}

    max_drawdown_pct = fields.get("max_drawdown_pct", -10.0)
    action = fields.get("action", "exit_all")
    recovery_threshold = fields.get("recovery_threshold", 5.0)

    positions = positions or []
    if not positions:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    passed, failed, symbol_results = [], [], []
    has_risk_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")

        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # 수익률·현재가는 **비교보다 먼저** 읽는다. 구 코드는 pos_data 원값을 그대로
        # ``drawdown <= max_drawdown_pct`` / ``round(pnl_rate, 2)`` 에 넣어, 값이
        # 숫자가 아니면('n/a'·None) TypeError 로 플러그인 전체가 죽었다. 못 읽은 값은
        # 0 으로 뭉개지 않고 그렇다고 표시한다(_position_qty 참조).
        raw_pnl_rate = pos_data.get("pnl_rate", 0)
        raw_current_price = pos_data.get("current_price", 0)
        pnl_rate = coerce_number(raw_pnl_rate)
        current_price = coerce_number(raw_current_price)

        # risk_tracker HWM 기반 drawdown (우선)
        drawdown = pnl_rate  # fallback (읽을 수 없으면 None)
        if has_risk_tracker:
            hwm = context.risk_tracker.get_hwm(symbol)
            if hwm and hwm.hwm_price > 0:
                drawdown = -float(hwm.drawdown_pct)  # drawdown_pct는 양수, 여기선 음수로 변환

        if drawdown is None:
            # pnl_rate 도 못 읽었고 HWM 도 없다 — 낙폭을 지어내지 않는다.
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "max_drawdown_pct": max_drawdown_pct,
                "action": "skip",
                "reason": (
                    f"수익률을 읽을 수 없어 낙폭을 판정하지 못함 (pnl_rate={raw_pnl_rate!r})"
                ),
            })
            continue

        triggered = drawdown <= max_drawdown_pct

        result_info = {
            "symbol": symbol, "exchange": exchange_name,
            "drawdown": round(drawdown, 2),
            "max_drawdown_pct": max_drawdown_pct,
            "triggered": triggered,
            "action": action if triggered else "hold",
        }
        if current_price is None:
            result_info["current_price_unavailable_reason"] = (
                f"현재가를 읽을 수 없음 (current_price={raw_current_price!r})"
            )
        else:
            result_info["current_price"] = current_price
        if pnl_rate is None:
            # HWM 으로 낙폭은 판정했지만 pnl_rate 자체는 못 읽은 경우.
            result_info["pnl_rate_unavailable_reason"] = (
                f"수익률을 읽을 수 없음 (pnl_rate={raw_pnl_rate!r}) — 낙폭은 HWM 기준"
            )
        else:
            result_info["pnl_rate"] = round(pnl_rate, 2)

        if has_risk_tracker:
            hwm = context.risk_tracker.get_hwm(symbol)
            if hwm:
                result_info["hwm_price"] = float(hwm.hwm_price)
                result_info["hwm_drawdown_pct"] = float(hwm.drawdown_pct)

        if triggered:
            # action에 따라 sell_quantity 설정
            if action == "reduce_half":
                qty = pos_data.get("qty", pos_data.get("quantity", 0))
                half = half_position_qty(qty)
                if half is None:
                    # 수량을 읽을 수 없으면(없음·문자열 쓰레기·NaN·0 이하) 임의의 수량을
                    # 지어내지 않는다. 왜 안 실었는지를 결과에 남긴다
                    # ('안 보낸 필드는 안 보냈다고 표시' 규약).
                    result_info["sell_quantity_unavailable_reason"] = (
                        f"보유 수량을 읽을 수 없어 절반 수량을 싣지 않음 (qty={qty!r})"
                    )
                else:
                    sym_dict["sell_quantity"] = half
                    result_info["sell_quantity"] = half
                    # 0 < 절반 < 1 이면 주문 송신부가 정수부 0 으로 접어 주문 자체를
                    # 만들지 않는다(_position_qty.below_broker_lot). 1주 보유의
                    # reduce_half 가 정확히 이 구간이다(0.5주). 수량은 그대로 둔다 —
                    # 정수화·올림은 송신부의 규약이다. 다만 '절반 축소했다고 보고했는데
                    # 아무 일도 없었다' 를 없애기 위해 사유를 드러낸다.
                    if below_broker_lot(half):
                        result_info["reduce_skipped_reason"] = (
                            f"절반 축소 수량 {half!r} 주는 1주 미만이라 주문 송신부가 정수부(0)로 "
                            f"접어 주문을 만들지 않는다 — 보유 {qty!r} 주에서 실제 축소가 "
                            "일어나지 않는다"
                        )
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append(result_info)

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
