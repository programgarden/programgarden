"""
Trailing Stop (가격 추적 정정 + 비율 기반 스케일링) 플러그인

기능:
1. 기존: 미체결 주문 가격 추적 정정 (price_gap_percent 기반)
2. 신규: 비율 기반 스케일링 트레일링 스탑 (trail_ratio + HWM 기반)
   - context.risk_tracker가 있으면 HWM drawdown으로 자동 매도 신호 생성
   - risk_tracker가 없으면 기존 로직으로 fallback
"""

from typing import Any, ClassVar, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언: HWM 추적이 필요함
risk_features: Set[str] = {"hwm"}

TRAILING_STOP_SCHEMA = PluginSchema(
    id="TrailingStop",
    name="Trailing Stop",
    category=PluginCategory.POSITION,
    version="2.0.0",
    description="Automatically adjusts unfilled order prices to track current price. With risk_tracker, provides ratio-based scaling trailing stop.",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "price_gap_percent": {
            "type": "float",
            "default": 0.5,
            "title": "Price Gap (%)",
            "description": "Difference from current price (for order modification mode)",
        },
        "max_modifications": {
            "type": "int",
            "default": 5,
            "title": "Max Modifications",
        },
        "trail_ratio": {
            "type": "float",
            "default": 0.3,
            "title": "Trailing Ratio",
            "description": "Trailing ratio (profit% x ratio = allowed drawdown). 0.3 = 30% of profit",
        },
    },
    tags=["modify", "tracking", "trailing_stop"],
    locales={
        "ko": {
            "name": "가격 추적 정정 (Trailing Stop)",
            "description": "미체결 주문의 가격을 현재가에 맞춰 자동 정정합니다. risk_tracker 연동 시 비율 기반 스케일링 트레일링 스탑을 제공합니다.",
            "fields.price_gap_percent": "가격 차이 (%)",
            "fields.max_modifications": "최대 정정 횟수",
            "fields.trail_ratio": "트레일링 비율 (수익률 × 비율 = 허용 하락폭)",
        },
    },
)


async def trailing_stop_condition(
    data: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    # 기존 호환용 파라미터
    target_orders: Optional[list] = None,
    ohlcv_data: Optional[dict] = None,
    **kwargs,
) -> dict:
    """가격 추적 정정 + 비율 기반 스케일링 트레일링 스탑

    risk_tracker가 있으면 HWM drawdown 기반 매도 신호를 생성합니다.
    스케일링 예시 (trail_ratio = 0.3):
      수익  5% → 트레일링  5% × 0.3 = 1.5% 하락 시 매도
      수익 10% → 트레일링 10% × 0.3 = 3.0% 하락 시 매도
      수익 20% → 트레일링 20% × 0.3 = 6.0% 하락 시 매도
    """
    if fields is None:
        fields = {}

    # ━━━ 비율 기반 스케일링 모드 (risk_tracker 연동) ━━━
    if context and hasattr(context, "risk_tracker") and context.risk_tracker:
        trail_ratio = fields.get("trail_ratio", 0.3)
        target_symbols = symbols or []

        passed_symbols = []
        failed_symbols = []
        symbol_results = []

        for sym_info in target_symbols:
            sym = sym_info.get("symbol", "") if isinstance(sym_info, dict) else sym_info
            exchange = sym_info.get("exchange", "") if isinstance(sym_info, dict) else ""

            hwm = context.risk_tracker.get_hwm(sym)
            if not hwm or hwm.position_avg_price <= 0:
                failed_symbols.append({"symbol": sym, "exchange": exchange})
                symbol_results.append({
                    "symbol": sym, "exchange": exchange,
                    "signal": "hold", "reason": "HWM 데이터 없음",
                })
                continue

            profit_pct = float(
                (hwm.hwm_price - hwm.position_avg_price)
                / hwm.position_avg_price * 100
            )
            threshold = max(profit_pct * trail_ratio, 1.0)  # 최소 1%
            drawdown = float(hwm.drawdown_pct)

            if drawdown > threshold:
                passed_symbols.append({"symbol": sym, "exchange": exchange})
                symbol_results.append({
                    "symbol": sym, "exchange": exchange,
                    "signal": "sell",
                    "reason": f"drawdown {drawdown:.1f}% > threshold {threshold:.1f}%",
                    "hwm_price": float(hwm.hwm_price),
                    "current_price": float(hwm.current_price),
                    "drawdown_pct": drawdown,
                    "threshold_pct": threshold,
                    "profit_pct": profit_pct,
                })
            else:
                failed_symbols.append({"symbol": sym, "exchange": exchange})
                symbol_results.append({
                    "symbol": sym, "exchange": exchange,
                    "signal": "hold",
                    "drawdown_pct": drawdown,
                    "threshold_pct": threshold,
                    "profit_pct": profit_pct,
                })

        return {
            "result": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,
            "failed_symbols": failed_symbols,
            "symbol_results": symbol_results,
        }

    # ━━━ 기존 모드: 미체결 주문 가격 추적 정정 ━━━
    if target_orders is None:
        target_orders = []
    if ohlcv_data is None:
        ohlcv_data = {}

    gap_percent = fields.get("price_gap_percent", 0.5)
    max_mods = fields.get("max_modifications", 5)

    modified = []

    for order in target_orders:
        symbol = order.get("symbol")

        # OHLCV 데이터에서 현재가 추출
        symbol_data = ohlcv_data.get(symbol, {})
        if isinstance(symbol_data, list) and symbol_data:
            current_price = symbol_data[-1].get("close", order.get("price", 100))
        elif isinstance(symbol_data, dict):
            current_price = symbol_data.get("close", symbol_data.get("current_price", order.get("price", 100)))
        else:
            current_price = order.get("price", 100)

        if order.get("side") == "buy":
            new_price = current_price * (1 - gap_percent / 100)
        else:
            new_price = current_price * (1 + gap_percent / 100)

        modified.append({
            "order_id": order.get("order_id"),
            "old_price": order.get("price"),
            "new_price": round(new_price, 2),
            "status": "modified",
        })

    return {
        "modified_orders": modified,
        "total_count": len(modified),
    }


__all__ = ["trailing_stop_condition", "TRAILING_STOP_SCHEMA", "risk_features"]
