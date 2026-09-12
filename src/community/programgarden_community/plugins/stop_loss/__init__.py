"""
Stop Loss (손절) 플러그인

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "pnl_rate": -5.2, "current_price": 150.0, ...}, ...]
- fields: {stop_percent}

※ 시계열 데이터(data) 불필요 - positions의 pnl_rate를 직접 사용
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import coerce_number, preserve_qty


STOP_LOSS_SCHEMA = PluginSchema(
    id="StopLoss",
    name="Stop Loss",
    category=PluginCategory.POSITION,
    version="3.1.0",
    description="Sells when losses exceed the set threshold to prevent larger losses. Example: Auto-sell at -3% loss.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "stop_percent": {
            "type": "float",
            "default": -3.0,
            "title": "Stop Loss (%)",
            "description": "Loss threshold as a negative percent (e.g. -3.0 = sell at a -3% loss). Must be < 0.",
            "lt": 0.0,
        },
    },
    required_data=["positions"],  # 시계열 데이터 불필요, positions만 필요
    # items { from, extract } 필수 필드 (v3.0.0+) - positions 사용 시 빈 배열
    required_fields=[],  # positions 플러그인은 items 불필요
    optional_fields=[],
    tags=["exit", "risk", "realtime"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "current_price": {"type": "float", "description": "Current market price (absent when it could not be read; see current_price_unavailable_reason)"},
        "current_price_unavailable_reason": {"type": "str", "description": "Present when the position's current_price could not be read as a number (display only - the stop decision does not use it)"},
        "stop_percent": {"type": "float", "description": "Stop loss threshold (%)"},
        "triggered": {"type": "bool", "description": "Whether stop loss was triggered (pnl_rate <= stop_percent)"},
        "action": {"type": "str", "description": "'skip' when pnl_rate or the held quantity could not be read, so the stop was not evaluated (present only on skipped positions)"},
        "reason": {"type": "str", "description": "Why the position was skipped: names the unreadable field(s) and their raw values (present on the 'skip' action)"},
    },
    locales={
        "ko": {
            "name": "손절 라인 (Stop Loss)",
            "description": "보유 종목의 손실이 설정한 기준을 넘으면 매도하여 더 큰 손실을 방지합니다. 예: -3% 손실 시 자동 매도.",
            "fields.stop_percent": "손절 비율 (%)",
        },
    },
)


async def stop_loss_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    """
    손절 조건 플러그인

    Args:
        positions: RealAccountNode의 positions 출력 (list[dict])
                   [{"symbol": "AAPL", "pnl_rate": -5.2, "current_price": 150.0, ...}, ...]
        fields: {stop_percent: 손절 기준 %} (음수 권장, 예: -3.0)

    Returns:
        passed_symbols: 손절 기준 도달 종목 (매도 대상)
        failed_symbols: 미도달 종목
        symbol_results: 종목별 상세 결과
    """
    if fields is None:
        fields = {}

    stop_percent = fields.get("stop_percent", fields.get("percent", -3.0))
    # stop_percent must be a strictly negative percent. Reject non-negative
    # values loudly instead of silently flipping the sign — a 0-or-positive
    # threshold can never fire on a loss (pnl_rate <= stop_percent), so it
    # would either exit immediately or never, both silent misconfigurations.
    try:
        stop_percent = float(stop_percent)
    except (TypeError, ValueError):
        raise ValueError(
            f"StopLoss: 'stop_percent' must be a number, got {stop_percent!r}."
        )
    if stop_percent >= 0:
        raise ValueError(
            "StopLoss: 'stop_percent' must be negative "
            "(e.g. -3.0 means a -3% stop-loss line). "
            f"Got {stop_percent}. A zero or positive threshold can never trigger "
            "on a loss. To exit a position while it is in profit, use the "
            "ProfitTarget or TrailingStop plugin instead."
        )

    positions = positions or []
    if not positions:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "error": "positions 데이터가 없습니다. RealAccountNode 또는 AccountNode의 positions를 연결하세요.",
        }

    passed, failed, symbol_results = [], [], []

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")

        # market_code를 거래소명으로 변환 (숫자 코드일 때만)
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        close_side = pos_data.get("close_side", "sell")

        # 수익률·수량은 **비교보다 먼저** 읽는다. 구 코드는 pos_data 원값을 그대로
        # ``round(pnl_rate, 2)`` / ``pnl_rate <= stop_percent`` 에 넣어, 값이 숫자가
        # 아니면('n/a'·None) TypeError 로 플러그인 전체가 죽었다. 못 읽은 값은 0 으로
        # 뭉개지 않고 어느 필드가 어떤 원값이었는지를 남긴 뒤 건너뛴다
        # ('안 보낸 필드는 안 보냈다고 표시' 규약, _position_qty 참조).
        # positions에서 직접 pnl_rate 사용 (이미 계산되어 있음)
        raw_pnl_rate = pos_data.get("pnl_rate", 0)
        raw_current_price = pos_data.get("current_price", 0)
        # 하위 주문 노드가 {{ item.quantity }} / {{ item.close_side }} 로 소비하므로
        # 전량 청산 수량과 청산 방향을 passed_symbols 에 함께 실어야 한다.
        # (누락 시 order 정규화가 quantity<=0 으로 주문을 조용히 버린다.)
        raw_qty = pos_data.get("quantity", pos_data.get("qty", 0))

        pnl_rate = coerce_number(raw_pnl_rate)
        current_price = coerce_number(raw_current_price)
        # 수량은 절단하지 않는다 — 정수화는 주문 송신부(_normalize_order)의 규약이다.
        quantity = preserve_qty(raw_qty)

        unreadable = []
        if pnl_rate is None:
            unreadable.append(f"pnl_rate={raw_pnl_rate!r}")
        if quantity is None:
            # 수량 없이는 청산 주문을 실을 수 없다(송신부가 quantity<=0 으로 조용히
            # 버린다) — 지어내지 않고 여기서 사유를 남긴다.
            unreadable.append(f"quantity={raw_qty!r}")
        if unreadable:
            failed.append({"exchange": exchange_name, "symbol": symbol, "close_side": close_side})
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange_name,
                "stop_percent": stop_percent,
                "action": "skip",
                "reason": (
                    "포지션 값을 읽을 수 없어 손절을 평가하지 못함 ("
                    + ", ".join(unreadable) + ")"
                ),
            })
            continue

        sym_dict = {
            "exchange": exchange_name,
            "symbol": symbol,
            "quantity": quantity,
            "close_side": close_side,
        }

        triggered = pnl_rate <= stop_percent
        entry = {
            "symbol": symbol,
            "exchange": exchange_name,
            "pnl_rate": round(pnl_rate, 2),
            "stop_percent": stop_percent,
            "triggered": triggered,
        }
        if current_price is None:
            # 현재가는 표시용이다(손절 판정은 pnl_rate 만 쓴다) — 못 읽었으면 0 으로
            # 싣지 않고 그렇다고 표시한다.
            entry["current_price_unavailable_reason"] = (
                f"현재가를 읽을 수 없음 (current_price={raw_current_price!r})"
            )
        else:
            entry["current_price"] = current_price
        symbol_results.append(entry)

        # 손절 조건: pnl_rate가 stop_percent 이하 (예: -21.95 <= -3.0)
        if triggered:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],  # 시계열 데이터 없음
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "StopLoss",
            "stop_percent": stop_percent,
            "total_positions": len(positions),
            "triggered_count": len(passed),
        },
    }


__all__ = ["stop_loss_condition", "STOP_LOSS_SCHEMA"]
