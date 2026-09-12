"""
PartialTakeProfit (분할 익절) 플러그인

여러 단계에서 분할 매도하여 리스크를 줄이면서 수익 확보.
- levels: [{pnl_pct: 5, sell_pct: 50}, {pnl_pct: 10, sell_pct: 30}, {pnl_pct: 20, sell_pct: 20}]
- strategy_state로 완료된 단계 추적 (⚠️ 의도일 뿐 — 아래 '상태 경로는 라이브에서
  동작하지 않는다' 절 참조)
- 포지션 청산 시 상태 자동 삭제 (같은 이유로 미검증)

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "pnl_rate": 6.5, "qty": 100, ...}, ...]
- fields: {levels}
- context: strategy_state 접근용 (선택)

🔴 상태(strategy_state) 경로는 현재 **라이브에서 동작하지 않는다** (관측 2026-09-12)
--------------------------------------------------------------------------------
아래 ``get_state``/``set_state``/``delete_state`` 헬퍼는 두 가지 이유로 실행기
경로에서 실제로 돌지 않는다. 둘 다 이 파일 밖(엔진 쪽)의 문제이며 여기서 고치지
않는다 — 아래 분기는 **미검증**이다.

1. 메서드 이름이 실제 트래커와 다르다. 실제 클래스
   ``programgarden.database.workflow_risk_tracker.WorkflowRiskTracker`` 에는
   ``get_state``/``set_state`` 가 **없다** — 있는 것은 ``save_state`` /
   ``load_state`` / ``load_states`` / ``delete_state`` / ``delete_states`` 뿐이다
   (그리고 이것들은 async 가 아니라 동기 메서드다). 실제 트래커를 가진 context 를
   넘기면 이 경로는 ``AttributeError: 'WorkflowRiskTracker' object has no
   attribute 'get_state'`` 로 즉사한다(실제 트래커 인스턴스로 재현 확인).
2. 애초에 context 가 오지 않는다. 이 플러그인은 ``required_data=["positions"]``
   라 실행기의 **positions 기반 분기**로 도는데, 그 분기
   (``ConditionNodeExecutor.execute``, programgarden/executor.py — plugin_kwargs 가
   ``{"positions": positions, "fields": evaluated_fields}`` 로 고정)는 ``context``
   를 넘기지 않는다. 그래서 라이브에서는 항상 ``has_state`` 가 False 이고 상태는
   저장·복원되지 않는다(context 없이 연속 호출하면 매번 같은 단계가 재발동하는
   것으로 재현 확인).

따라서 위 docstring 의 "strategy_state 로 ... 추적/저장" 은 **의도**이지 현재
동작이 아니다. 이 경로를 되살리려면 (a) 메서드명을 실제 트래커에 맞추고,
(b) 실행기의 positions 분기가 context 를 넘기게 하고, (c) 동기/비동기 호출 규약을
맞춰야 한다 — 전부 이 플러그인 파일 밖의 수정이다.
"""

import json
from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import (
    below_broker_lot,
    coerce_number,
    coerce_qty,
    partial_sell_qty,
    preserve_qty,
)


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
        "qty": {"type": "float", "description": "Current position quantity (fractional share counts are kept, not truncated; the raw unparsed value is echoed here on the 'skip' action that reports an unreadable quantity)"},
        "sell_quantity": {"type": "float", "description": "Quantity to sell at this partial take profit level (original quantity x sell_pct, capped at the held quantity; fractional results are kept, not truncated - the order node truncates to the broker lot and reports the remainder)"},
        "reason": {"type": "str", "description": "Why this level was skipped or cleared (present on 'skip' and 'cleared' actions)"},
        "sell_pct": {"type": "float", "description": "Percentage of position to sell (%)"},
        "level_index": {"type": "int", "description": "Index of the triggered profit level"},
        "remaining_levels": {"type": "int", "description": "Number of remaining profit levels not yet triggered"},
        "action": {"type": "str", "description": "Action taken: 'sell', 'hold', 'skip', or 'cleared'"},
        "reduce_skipped_reason": {"type": "str", "description": "Present on a 'sell' action whose sell quantity is below 1 share: the order node truncates to the integer part (0) and builds no order, so no sell actually happens this round"},
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
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """
    분할 익절 조건 평가

    Args:
        positions: RealAccountNode의 positions 출력 (list[dict])
                   [{"symbol": "AAPL", "pnl_rate": 6.5, "qty": 100, ...}, ...]
        fields: {levels: JSON string or list}
        context: strategy_state 접근용

    Returns:
        passed_symbols, failed_symbols, symbol_results (sell_quantity, sell_pct, level_index 포함)
    """
    if fields is None:
        fields = {}

    levels = _parse_levels(fields.get("levels", None))

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

    # strategy_state 접근 헬퍼.
    # 🔴 아래 세 함수는 라이브 실행기 경로에서 돌지 않는다 — 실행기의 positions 분기
    #    (ConditionNodeExecutor.execute)가 context 를 넘기지 않아 has_state 가 항상
    #    False 이고, 설령 실제 트래커를 넘겨도 WorkflowRiskTracker 에는
    #    get_state/set_state 가 없어 AttributeError 로 죽는다. 모듈 docstring 의
    #    '상태 경로는 라이브에서 동작하지 않는다' 절 참조. 미검증 분기.
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

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        raw_pnl_rate = pos_data.get("pnl_rate", 0)
        raw_qty = pos_data.get("qty", pos_data.get("quantity", 0))
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        # 하위 주문 노드가 {{ item.quantity }} / {{ item.close_side }} 로 소비하므로
        # 청산 방향을 함께 싣는다. 분할 익절은 '부분' 수량이므로 passed_symbols 의
        # quantity 는 아래 sell_quantity 로 통일한다(sell_quantity 는 하위 호환용으로
        # symbol_results 에 유지).
        close_side = pos_data.get("close_side", "sell")
        sym_dict = {"symbol": symbol, "exchange": exchange_name, "close_side": close_side}

        # 수량은 **비교보다 먼저** 읽는다. 구 코드는 pos_data 원값을 그대로
        # ``qty <= 0`` 에 넣어, 수량이 숫자가 아니면('100'·'n/a'·None) 거기서
        # TypeError 로 플러그인 전체가 죽었다. 그래서 아래 '수량을 못 읽었다'
        # 사유 분기는 수량에 대해서는 **도달할 수 없었다**.
        qty = preserve_qty(raw_qty)
        if qty is None:
            failed.append(sym_dict)
            skipped = {
                "symbol": symbol, "exchange": exchange_name,
                "qty": raw_qty,
                "action": "skip",
                "reason": (
                    f"보유 수량을 읽을 수 없어 분할 익절을 평가하지 못함 (qty={raw_qty!r})"
                ),
            }
            # pnl_rate 는 읽힐 때만 싣는다(못 읽은 값을 0 으로 지어내지 않는다).
            pnl_display = coerce_number(raw_pnl_rate)
            if pnl_display is not None:
                skipped["pnl_rate"] = round(pnl_display, 2)
            symbol_results.append(skipped)
            continue

        # 수량 0이면 청산 완료 → 상태 삭제
        if qty <= 0:
            await delete_state(f"partial_tp.{symbol}.completed_levels")
            await delete_state(f"partial_tp.{symbol}.original_qty")
            failed.append(sym_dict)
            cleared = {
                "symbol": symbol, "exchange": exchange_name, "qty": qty,
                "action": "cleared", "reason": "Position closed",
            }
            pnl_display = coerce_number(raw_pnl_rate)
            if pnl_display is not None:
                cleared["pnl_rate"] = round(pnl_display, 2)
            symbol_results.append(cleared)
            continue

        # 수익률도 **비교보다 먼저** 읽는다. 구 코드는 원값을 그대로
        # ``pnl_rate >= level["pnl_pct"]`` / ``round(pnl_rate, 2)`` 에 넣어 값이 숫자가
        # 아니면('n/a'·None) TypeError 로 죽었다. 수익률 없이는 어느 단계도 판정할 수
        # 없으므로 상태를 건드리지 않고 사유만 남긴다.
        pnl_rate = coerce_number(raw_pnl_rate)
        if pnl_rate is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name, "qty": qty,
                "action": "skip",
                "reason": (
                    f"수익률을 읽을 수 없어 분할 익절을 평가하지 못함 (pnl_rate={raw_pnl_rate!r})"
                ),
            })
            continue

        # 완료된 단계 로드
        completed_raw = await get_state(f"partial_tp.{symbol}.completed_levels")
        completed_levels = completed_raw if isinstance(completed_raw, list) else []

        original_qty_raw = await get_state(f"partial_tp.{symbol}.original_qty")
        # Decimal 로 복원되는 저장값도 받아들인다(구 isinstance(int, float) 검사는
        # Decimal 을 놓쳐 매 단계 '현재 수량' 기준으로 되돌아갔다).
        # ⚠️ 이 분기는 **라이브에서 도달하지 않는다** — get_state 가 항상 None 을
        #    돌려주므로(모듈 docstring 의 '상태 경로' 절) original_qty 는 늘 아래
        #    폴백인 현재 qty 가 된다. Decimal 복원 자체는 목(MockRiskTracker)에서만
        #    검증됐다.
        original_qty_state = coerce_qty(original_qty_raw)
        original_qty = (
            original_qty_state
            if original_qty_state is not None and original_qty_state > 0
            else qty
        )

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
            # 소수 잔량 보존 — int() 절단은 0.532주 포지션의 부분 익절을 0 으로
            # 만들어 아래 게이트에서 통째로 스킵시켰다(_position_qty.partial_sell_qty).
            sell_quantity = partial_sell_qty(original_qty, sell_pct, qty)

            if sell_quantity is None:
                # 수량/비율을 읽을 수 없으면 지어내지 않는다. 왜 못 실었는지를 남긴다
                # ('안 보낸 필드는 안 보냈다고 표시' 규약).
                failed.append(sym_dict)
                symbol_results.append({
                    "symbol": symbol, "exchange": exchange_name,
                    "pnl_rate": round(pnl_rate, 2), "qty": qty,
                    "sell_pct": sell_pct, "level_index": level_idx,
                    "action": "skip",
                    "reason": (
                        "수량을 읽을 수 없어 부분 익절 수량을 계산하지 못함 "
                        f"(original_qty={original_qty!r}, sell_pct={sell_pct!r}, qty={qty!r})"
                    ),
                })
            elif sell_quantity > 0:
                # 완료 단계 업데이트
                new_completed = completed_levels + [level_idx]
                await set_state(f"partial_tp.{symbol}.completed_levels", new_completed)
                if not completed_levels:
                    await set_state(f"partial_tp.{symbol}.original_qty", qty)

                remaining_levels = len(levels) - len(new_completed)

                # 부분 청산 수량을 quantity 로 실어 주문 노드가 부분 매도하도록 한다.
                passed.append({**sym_dict, "quantity": sell_quantity})
                sold = {
                    "symbol": symbol, "exchange": exchange_name,
                    "pnl_rate": round(pnl_rate, 2), "qty": qty,
                    "sell_quantity": sell_quantity, "sell_pct": sell_pct,
                    "level_index": level_idx, "remaining_levels": remaining_levels,
                    "action": "sell",
                }
                # 0 < 수량 < 1 이면 주문 송신부가 정수부 0 으로 접어 **주문을 만들지
                # 않는다** (_position_qty.below_broker_lot 참조). 수량은 그대로 두되
                # (정수화·올림은 송신부의 규약이다) 조용한 무동작이 되지 않도록
                # 사유를 드러낸다.
                if below_broker_lot(sell_quantity):
                    sold["reduce_skipped_reason"] = (
                        f"부분 익절 수량 {sell_quantity!r} 주는 1주 미만이라 주문 송신부가 "
                        "정수부(0)로 접어 주문을 만들지 않는다 — 이번 회차에는 실제 매도가 "
                        "일어나지 않는다"
                    )
                symbol_results.append(sold)
            else:
                failed.append(sym_dict)
                symbol_results.append({
                    "symbol": symbol, "exchange": exchange_name,
                    "pnl_rate": round(pnl_rate, 2), "qty": qty,
                    "sell_quantity": sell_quantity, "sell_pct": sell_pct,
                    "level_index": level_idx,
                    "action": "skip",
                    "reason": (
                        f"부분 익절 수량이 0 — 매도 비율 {sell_pct!r}% × 기준 수량 "
                        f"{original_qty!r} (보유 {qty!r})"
                    ),
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
