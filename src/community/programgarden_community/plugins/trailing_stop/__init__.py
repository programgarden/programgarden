"""
Trailing Stop (가격 추적 정정 + HWM 트레일링 스탑) 플러그인

기능:
1. 기존: 미체결 주문 가격 추적 정정 (price_gap_percent 기반)
2. 비율 기반 스케일링 트레일링 스탑 (trail_ratio + HWM 기반)
   - context.risk_tracker가 있으면 HWM drawdown으로 자동 매도 신호 생성
   - risk_tracker가 없으면 기존 로직으로 fallback
3. 고정 % 트레일링 스탑 (trail_percent, v2.1.0)
   - trail_percent > 0 이면 고점(HWM) 대비 고정 % 하락 시 매도 신호
     (예: trail_percent=5.0 → 고점 대비 -5% 도달 시 sell)
   - 공급된 data 행의 close 로 HWM 을 플러그인이 직접 갱신하므로
     실시간 P&L 틱 리스너 없는 스케줄 폴링 구성에서도 트레일링이 동작
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
    version="2.1.0",
    description="Automatically adjusts unfilled order prices to track current price. With risk_tracker, provides HWM trailing stop: fixed percent (trail_percent) or ratio-based scaling (trail_ratio).",
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
        "trail_percent": {
            "type": "float",
            "default": 0.0,
            "title": "Fixed Trail (%)",
            "description": "Fixed trailing-stop percent off the high-water mark. E.g. 5.0 = sell when price falls 5% from HWM. 0 disables fixed mode and uses trail_ratio scaling instead.",
        },
    },
    tags=["modify", "tracking", "trailing_stop"],
    output_fields={
        "signal": {"type": "str", "description": "Trading signal: 'sell' (trailing stop triggered) or 'hold'"},
        "hwm_price": {"type": "float", "description": "High-water mark price tracked by risk_tracker"},
        "current_price": {"type": "float", "description": "Current market price"},
        "drawdown_pct": {"type": "float", "description": "Current drawdown from high-water mark (%)"},
        "threshold_pct": {"type": "float", "description": "Allowed drawdown threshold (%) before sell signal"},
        "profit_pct": {"type": "float", "description": "Profit percentage from entry to high-water mark"},
    },
    locales={
        "ko": {
            "name": "가격 추적 정정 (Trailing Stop)",
            "description": "미체결 주문의 가격을 현재가에 맞춰 자동 정정합니다. risk_tracker 연동 시 비율 기반 스케일링 트레일링 스탑을 제공합니다.",
            "fields.price_gap_percent": "가격 차이 (%)",
            "fields.max_modifications": "최대 정정 횟수",
            "fields.trail_ratio": "트레일링 비율 (수익률 × 비율 = 허용 하락폭)",
            "fields.trail_percent": "고정 트레일링 % (고점 대비 하락폭, 0=비율 모드)",
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
    """가격 추적 정정 + HWM 트레일링 스탑 (고정 % / 비율 스케일링)

    risk_tracker가 있으면 HWM drawdown 기반 매도 신호를 생성합니다.

    고정 모드 (trail_percent > 0):
      trail_percent=5.0 → 고점(HWM) 대비 -5% 도달 시 매도 (drawdown >= 5%)

    스케일링 모드 (trail_percent == 0, trail_ratio 사용):
      수익  5% → 트레일링  5% × 0.3 = 1.5% 하락 시 매도
      수익 10% → 트레일링 10% × 0.3 = 3.0% 하락 시 매도
      수익 20% → 트레일링 20% × 0.3 = 6.0% 하락 시 매도

    두 모드 모두 data 행의 close 로 HWM 을 플러그인이 직접 갱신합니다
    (스케줄 폴링 구성에서 P&L 틱 리스너 부재 시에도 트레일링 동작).
    """
    if fields is None:
        fields = {}

    # ━━━ HWM 트레일링 모드 (risk_tracker 연동: trail_percent 고정 % 또는 trail_ratio 스케일링) ━━━
    if context and hasattr(context, "risk_tracker") and context.risk_tracker:
        trail_ratio = fields.get("trail_ratio", 0.3)
        try:
            trail_percent = float(fields.get("trail_percent", 0.0) or 0.0)
        except (TypeError, ValueError):
            trail_percent = 0.0
        target_symbols = symbols or []

        # data 행(예: AccountNode positions 스냅샷의 close=current_price)에서
        # 종목별 최신 close 를 추출해 HWM 을 직접 갱신한다.
        # P&L 틱 리스너가 없는 스케줄 폴링 구성에서도 HWM 이 전진하도록 보장.
        latest_close: Dict[str, float] = {}
        for row in data or []:
            if not isinstance(row, dict):
                continue
            row_sym = row.get("symbol")
            row_close = row.get("close")
            if not row_sym or row_close is None:
                continue
            try:
                close_val = float(row_close)
            except (TypeError, ValueError):
                continue
            if close_val > 0:
                latest_close[row_sym] = close_val

        passed_symbols = []
        failed_symbols = []
        symbol_results = []

        for sym_info in target_symbols:
            sym = sym_info.get("symbol", "") if isinstance(sym_info, dict) else sym_info
            exchange = sym_info.get("exchange", "") if isinstance(sym_info, dict) else ""

            hwm = context.risk_tracker.get_hwm(sym)
            close_val = latest_close.get(sym)
            if hwm is not None and close_val is not None:
                # 등록된(이 워크플로우가 매수한) 심볼만 가격 갱신 —
                # 미등록 외부 보유 종목은 HWM/price window 모두 건드리지 않음
                context.risk_tracker.update_price(sym, exchange, close_val)
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
            if trail_percent > 0:
                threshold = trail_percent  # 고정 %: 고점 대비 trail_percent 하락 시 매도
            else:
                threshold = max(profit_pct * trail_ratio, 1.0)  # 스케일링: 최소 1%
            drawdown = float(hwm.drawdown_pct)

            triggered = (drawdown >= threshold) if trail_percent > 0 else (drawdown > threshold)
            if triggered:
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
