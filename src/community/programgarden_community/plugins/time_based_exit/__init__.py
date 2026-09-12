"""
TimeBasedExit (시간 기반 청산) 플러그인

보유 기간이 설정된 일수를 초과하면 자동 청산 시그널 발생.
- strategy_state 에 진입일(이 플러그인이 포지션을 **처음 관측한 날**) 저장
- 포지션 청산(qty 0) 시 상태 자동 삭제
- 포지션이 사라진 종목(positions 에 더 이상 없음)의 상태도 자동 정리

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "qty": 100, ...}, ...]
- fields: {max_hold_days, warn_days}
- context: strategy_state 접근용 (선택)

상태(strategy_state) 경로 — 2026-09-12 수정 전/후
--------------------------------------------------------------------------------
2026-09-12 이전에는 이 경로가 **라이브에서 죽어 있었다**. 두 가지 이유였고 둘 다
이번에 닫혔다:

1. 메서드 이름·호출 규약이 실제 트래커와 달랐다. 실제 클래스
   ``programgarden.database.workflow_risk_tracker.WorkflowRiskTracker`` 에는
   ``get_state``/``set_state`` 가 **없다** — 있는 것은 ``save_state`` /
   ``load_state`` / ``load_states`` / ``delete_state`` / ``delete_states`` 이고
   전부 **동기** 메서드다. 실제 트래커를 넘기면 첫 포지션에서
   ``AttributeError: 'WorkflowRiskTracker' object has no attribute 'get_state'`` 로
   즉사했다(실제 인스턴스로 재현). 아래 헬퍼는 이제 실제 이름을 동기 호출한다.
2. 애초에 context 가 오지 않았다. 이 플러그인은 ``required_data=["positions"]``
   라 실행기의 positions 기반 분기로 도는데, 그 분기(``ConditionNodeExecutor.execute``)
   가 plugin_kwargs 를 ``{"positions", "fields"}`` 로 고정해 ``context`` 를 넘기지
   않았다. 이제 items/data 기반 분기와 같은 규약으로 **시그니처에 context 가 있으면
   넘긴다**(executor 쪽 수정).

켜졌을 때의 의미 (수정 전과 달라지는 동작)
- 수정 전: 매 사이클 entry_date=오늘 → hold_days=0 → **영영 청산하지 않았다**.
- 수정 후: entry_date 는 이 플러그인이 그 종목을 **처음 관측한 날**로 고정되고 이후
  사이클에서 덮어쓰지 않는다 → hold_days 가 실제로 자라 max_hold_days 에 exit 가 난다.
  ⚠️ '진입일' 은 브로커 체결일이 아니다. 워크플로우가 돌기 전부터 보유하던 포지션은
  워크플로우 **첫 실행일**이 진입일이 된다(output_fields.entry_date 설명 참조).
- 저장 형식: ISO 문자열 ``YYYY-MM-DD``. 트래커는 str 을 'string' 타입으로 저장하고
  그대로 되돌려주므로(``_serialize_state_value``/``_deserialize_state_value``)
  ``date.fromisoformat`` 로 바로 복원된다. datetime/Decimal 을 싣지 않는다.
- 저장 범위: 트래커 DB 는 ``{workflow_id}_workflow.db``, 키는 (product, provider,
  trading_mode) 로 스코프된다 → 같은 워크플로우를 **재시작해도 entry_date 가 복원**된다.
  다른 워크플로우는 다른 DB 라 서로 보이지 않는다.
- 정리: qty 0 인 종목은 그 자리에서 삭제하고, positions 에 **없는** 종목(전량 매도 후
  브로커가 목록에서 뺀 경우)은 사이클 끝에 ``load_states("time_exit.")`` 로 훑어 지운다
  (positions 가 비어 있으면 전부 지운다 — 계좌가 비었다는 뜻이다). 정리하지 않으면
  재매수 직후 옛 entry_date 로 hold_days 가 커져 **거짓 exit** 가 나기 때문이다.
  같은 워크플로우에 TimeBasedExit 노드를 둘 이상 두고 positions 를 종목별로 갈라
  넣는 구성은 키 네임스페이스(``time_exit.{symbol}.entry_date``)를 공유하므로
  지원하지 않는다.
- 강등: 트래커에 ``load_state``/``save_state``/``delete_state`` 셋이 전부 없으면(다른
  트래커 변종) 상태 경로를 켜지 않고 **무상태로 강등**한다 — 크래시 대신 context 없이
  부른 것과 같은 종전 동작(hold_days=0)이다. ``state`` feature 없이 만들어진 실제
  트래커도 같다(load_state→None, save_state→False). dry_run 에서는 트래커 자체가 뜨지
  않는다.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import preserve_qty

logger = logging.getLogger(__name__)


# risk_features: strategy_state 사용
risk_features: Set[str] = {"state"}

_STATE_PREFIX = "time_exit."
_STATE_SUFFIX = ".entry_date"

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
        "entry_date": {"type": "str", "description": "Entry date as first observed by this plugin (YYYY-MM-DD) - the first workflow cycle that saw the position, not the broker fill date"},
        "hold_days": {"type": "int", "description": "Number of days position has been held (today - entry_date)"},
        "max_hold_days": {"type": "int", "description": "Maximum allowed holding days"},
        "warn": {"type": "bool", "description": "Whether the warning threshold has been crossed"},
        "action": {"type": "str", "description": "Recommended action: 'exit', 'warn', 'hold', 'cleared', or 'skip'"},
        "reason": {"type": "str", "description": "Why the position was cleared or skipped (present on the 'cleared' and 'skip' actions)"},
    },
    locales={
        "ko": {
            "name": "시간 기반 청산",
            "description": "보유 기간이 설정된 일수를 초과하면 자동으로 청산 시그널을 발생시킵니다. 처음 관측한 날을 진입일로 기록해 추적합니다.",
            "fields.max_hold_days": "최대 보유 일수",
            "fields.warn_days": "경고 시작 일수 (0 = 비활성)",
        },
    },
)


def _entry_date_key(symbol: str) -> str:
    return f"{_STATE_PREFIX}{symbol}{_STATE_SUFFIX}"


def _sweep_stale_entry_dates(tracker: Any, present_symbols: Set[str]) -> List[str]:
    """positions 에 더 이상 없는 종목의 entry_date 상태를 지운다 (모듈 docstring '정리' 절).

    ``load_states(prefix)`` 가 없는 트래커 변종이면 정리하지 않는다(무상태 강등과 같은
    규약). 심볼에 점이 들어갈 수 있으므로(BRK.B) 키를 '.' 로 split 하지 않고
    접두·접미를 잘라 심볼을 얻는다. 지운 심볼 목록을 돌려준다.
    """
    if tracker is None:
        return []
    load_states = getattr(tracker, "load_states", None)
    if not callable(load_states):
        return []
    removed: List[str] = []
    try:
        keys = list(load_states(_STATE_PREFIX).keys())
    except Exception as e:
        logger.warning(f"TimeBasedExit: 상태 정리용 조회 실패 (prefix={_STATE_PREFIX}): {e}")
        return []
    for key in keys:
        if not key.endswith(_STATE_SUFFIX):
            continue
        symbol = key[len(_STATE_PREFIX):-len(_STATE_SUFFIX)]
        if not symbol or symbol in present_symbols:
            continue
        try:
            tracker.delete_state(key)
            removed.append(symbol)
        except Exception as e:
            logger.warning(f"TimeBasedExit: 상태 정리 실패 ({key}): {e}")
    return removed


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

    # strategy_state 접근 헬퍼.
    # 메서드 이름·호출 규약은 **실제 트래커**(WorkflowRiskTracker)에 맞춘다 —
    # load_state / save_state / delete_state 이고 전부 동기다(await 하지 않는다).
    # 셋이 전부 있을 때만 상태 경로를 켠다. 다른 트래커 변종이면 크래시 대신 무상태로
    # 강등한다. 모듈 docstring 의 '상태 경로' 절 참조.
    _tracker = getattr(context, "risk_tracker", None) if context else None
    has_state = _tracker is not None and all(
        hasattr(_tracker, name) for name in ("load_state", "save_state", "delete_state")
    )

    def get_state(key: str) -> Any:
        if has_state:
            return _tracker.load_state(key)
        return None

    def set_state(key: str, value: Any) -> None:
        if not has_state:
            return
        try:
            if not _tracker.save_state(key, value):
                logger.warning(
                    f"TimeBasedExit: 상태 저장 실패 ({key}) — 트래커가 False 를 돌려줌 "
                    "('state' feature 없음 또는 DB 쓰기 실패)"
                )
        except Exception as e:
            logger.warning(f"TimeBasedExit: 상태 저장 실패 ({key}): {e}")

    def delete_state(key: str) -> None:
        if not has_state:
            return
        try:
            _tracker.delete_state(key)
        except Exception as e:
            logger.warning(f"TimeBasedExit: 상태 삭제 실패 ({key}): {e}")

    positions = positions or []
    if not positions:
        # 계좌가 비었다 — 남아 있는 entry_date 는 전부 '사라진 종목' 의 것이다.
        stale = _sweep_stale_entry_dates(_tracker if has_state else None, set())
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No positions data", "stale_state_cleared": stale},
        }

    today = date.today()
    today_str = today.isoformat()

    passed, failed, symbol_results = [], [], []
    present_symbols: Set[str] = set()

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        present_symbols.add(symbol)
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
            delete_state(_entry_date_key(symbol))
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange_name,
                "action": "cleared", "reason": "Position closed",
            })
            continue

        # 진입일 로드 또는 최초 감지 — 처음 관측한 날을 고정하고 이후엔 덮어쓰지 않는다
        entry_date_str = get_state(_entry_date_key(symbol))
        if not entry_date_str:
            entry_date_str = today_str
            set_state(_entry_date_key(symbol), entry_date_str)

        try:
            entry_date = date.fromisoformat(entry_date_str)
        except (ValueError, TypeError):
            # 읽을 수 없는 저장값(형식 불일치)은 오늘로 다시 고정한다 — 사유를 남긴다.
            logger.warning(
                f"TimeBasedExit: 저장된 진입일을 읽을 수 없어 오늘로 재설정 "
                f"(symbol={symbol}, value={entry_date_str!r})"
            )
            entry_date = today
            entry_date_str = today_str
            set_state(_entry_date_key(symbol), today_str)

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

    # positions 에서 사라진 종목의 entry_date 정리 (모듈 docstring '정리' 절)
    stale = _sweep_stale_entry_dates(_tracker if has_state else None, present_symbols)

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
            "stale_state_cleared": stale,
        },
    }


__all__ = ["time_based_exit_condition", "TIME_BASED_EXIT_SCHEMA", "risk_features"]
