"""
Profit Target (익절) 플러그인

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "pnl_rate": 6.3, "current_price": 150.0, ...}, ...]
- fields: {target_percent}

※ 시계열 데이터(data) 불필요 - positions의 pnl_rate를 직접 사용
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import coerce_number, preserve_qty


PROFIT_TARGET_SCHEMA = PluginSchema(
    id="ProfitTarget",
    name="Profit Target",
    category=PluginCategory.POSITION,
    version="3.1.0",
    description="Checks if holdings have reached the target profit rate. Example: Sell to realize profit when gain exceeds 5%.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "target_percent": {
            "type": "float",
            "default": 5.0,
            "title": "Target Profit (%)",
            "description": "Profit threshold as a positive percent (e.g. 5.0 = sell at a +5% gain). Must be > 0.",
            "gt": 0.0,
        },
    },
    required_data=["positions"],  # 시계열 데이터 불필요, positions만 필요
    # items { from, extract } 필수 필드 (v3.0.0+) - positions 사용 시 빈 배열
    required_fields=[],  # positions 플러그인은 items 불필요
    optional_fields=[],
    tags=["exit", "profit", "realtime"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "current_price": {"type": "float", "description": "Current market price (absent when it could not be read; see current_price_unavailable_reason)"},
        "current_price_unavailable_reason": {"type": "str", "description": "Present when the position's current_price could not be read as a number (display only - the target decision does not use it)"},
        "target_percent": {"type": "float", "description": "Profit target threshold (%)"},
        "reached": {"type": "bool", "description": "Whether profit target was reached (pnl_rate >= target_percent)"},
        "action": {"type": "str", "description": "'skip' when pnl_rate or the held quantity could not be read, so the target was not evaluated (present only on skipped positions)"},
        "reason": {"type": "str", "description": "Why the position was skipped: names the unreadable field(s) and their raw values (present on the 'skip' action)"},
    },
    locales={
        "ko": {
            "name": "목표 수익률 (Profit Target)",
            "description": "보유 종목이 목표 수익률에 도달했는지 확인합니다. 예: 5% 이상 수익이 나면 매도하여 수익 실현.",
            "fields.target_percent": "목표 수익률 (%)",
        },
    },
)


async def profit_target_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    """
    익절 조건 플러그인

    Args:
        positions: RealAccountNode의 positions 출력 (list[dict])
                   [{"symbol": "AAPL", "pnl_rate": 6.3, "current_price": 150.0, ...}, ...]
        fields: {target_percent: 목표 수익률 %}

    Returns:
        passed_symbols: 목표 수익률 달성 종목
        failed_symbols: 미달성 종목
        symbol_results: 종목별 상세 결과
    """
    if fields is None:
        fields = {}

    target_percent = fields.get("target_percent", fields.get("percent", 5.0))
    # target_percent must be a strictly positive percent. Reject non-positive
    # values loudly — a 0-or-negative target can never fire on a gain
    # (pnl_rate >= target_percent would match a loss or every position),
    # a silent misconfiguration.
    try:
        target_percent = float(target_percent)
    except (TypeError, ValueError):
        raise ValueError(
            f"ProfitTarget: 'target_percent' must be a number, got {target_percent!r}."
        )
    if target_percent <= 0:
        raise ValueError(
            "ProfitTarget: 'target_percent' must be positive "
            "(e.g. 5.0 means a +5% profit target). "
            f"Got {target_percent}. A zero or negative target can never trigger "
            "on a gain. To exit a position while it is at a loss, use the "
            "StopLoss or TrailingStop plugin instead."
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

        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        close_side = pos_data.get("close_side", "sell")

        # 수익률·수량은 **비교보다 먼저** 읽는다. 구 코드는 pos_data 원값을 그대로
        # ``round(pnl_rate, 2)`` / ``pnl_rate >= target_percent`` 에 넣어, 값이 숫자가
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
                "target_percent": target_percent,
                "action": "skip",
                "reason": (
                    "포지션 값을 읽을 수 없어 익절을 평가하지 못함 ("
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

        reached = pnl_rate >= target_percent
        entry = {
            "symbol": symbol,
            "exchange": exchange_name,
            "pnl_rate": round(pnl_rate, 2),
            "target_percent": target_percent,
            "reached": reached,
        }
        if current_price is None:
            # 현재가는 표시용이다(익절 판정은 pnl_rate 만 쓴다) — 못 읽었으면 0 으로
            # 싣지 않고 그렇다고 표시한다.
            entry["current_price_unavailable_reason"] = (
                f"현재가를 읽을 수 없음 (current_price={raw_current_price!r})"
            )
        else:
            entry["current_price"] = current_price
        symbol_results.append(entry)

        if reached:
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
            "indicator": "ProfitTarget",
            "target_percent": target_percent,
            "total_positions": len(positions),
            "reached_count": len(passed),
        },
    }


__all__ = ["profit_target_condition", "PROFIT_TARGET_SCHEMA"]
