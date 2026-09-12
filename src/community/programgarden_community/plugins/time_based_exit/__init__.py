"""
TimeBasedExit (시간 기반 청산) 플러그인

보유 기간이 설정된 일수를 초과하면 자동 청산 시그널 발생.
- strategy_state에 진입일 저장 (⚠️ 의도일 뿐 — 아래 '상태 경로는 라이브에서
  동작하지 않는다' 절 참조)
- 포지션 청산 시 상태 자동 삭제 (같은 이유로 미검증)
- 포지션이 사라진 종목의 상태도 자동 정리

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "qty": 100, ...}, ...]
- fields: {max_hold_days, warn_days}
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

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import preserve_qty


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
        "action": {"type": "str", "description": "Recommended action: 'exit', 'warn', 'hold', 'cleared', or 'skip'"},
        "reason": {"type": "str", "description": "Why the position was cleared or skipped (present on the 'cleared' and 'skip' actions)"},
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

    today = date.today()
    today_str = today.isoformat()

    passed, failed, symbol_results = [], [], []

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        raw_qty = pos_data.get("qty", pos_data.get("quantity", 0))
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # 수량은 **비교보다 먼저** 읽는다. 구 코드는 pos_data 원값을 그대로
        # ``qty <= 0`` 에 넣어, 수량이 숫자가 아니면('100'·'n/a'·None) 거기서
        # TypeError 로 플러그인 전체가 죽었다 — '수량을 못 읽었다' 는 사실이
        # 결과에 남을 기회조차 없었다.
        qty = preserve_qty(raw_qty)
        if qty is None:
            # 읽을 수 없는 수량으로 보유일수를 판정하지 않는다. 상태(진입일)도
            # 건드리지 않는다 — 청산된 것인지 알 수 없기 때문이다.
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "action": "skip",
                "reason": (
                    f"보유 수량을 읽을 수 없어 보유 기간을 판정하지 못함 (qty={raw_qty!r})"
                ),
            })
            continue

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
