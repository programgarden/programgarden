"""
RollManagement (롤오버 관리) 플러그인 - 선물 전용

선물 만기 전 자동 롤오버 시그널 생성.
월물 코드에서 만기를 추출하여 잔여일 기반 롤오버 타이밍 결정.

입력 형식:
- positions: 선물 포지션 (list[dict])
  예: [{"symbol": "HSIZ25", "qty": 1, "current_price": 17500.0, "exchange": "HKEX", ...}, ...]
- fields: {days_before_expiry, roll_strategy}
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언
risk_features: Set[str] = {"state"}

ROLL_MANAGEMENT_SCHEMA = PluginSchema(
    id="RollManagement",
    name="Roll Management",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Monitors days-to-expiry for futures contracts and generates roll signals. Recommends optimal roll timing to avoid forced liquidation.",
    products=[ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "days_before_expiry": {
            "type": "int",
            "default": 5,
            "title": "Days Before Expiry",
            "description": "Number of trading days before expiry to trigger roll signal",
            "ge": 1,
            "le": 30,
        },
        "roll_strategy": {
            "type": "string",
            "default": "calendar",
            "title": "Roll Strategy",
            "description": "How to determine roll timing",
            "enum": ["calendar", "volume", "spread_optimal"],
        },
    },
    required_data=["positions"],
    required_fields=[],
    optional_fields=[],
    tags=["futures", "roll", "expiry", "contract_management"],
    output_fields={
        "expiry_date": {"type": "str", "description": "Contract expiry date (YYYY-MM-DD)"},
        "days_to_expiry": {"type": "int", "description": "Number of days until contract expiry"},
        "should_roll": {"type": "bool", "description": "Whether it is time to roll to the next contract"},
        "next_contract": {"type": "str", "description": "Symbol of the next contract to roll into"},
        "roll_strategy": {"type": "str", "description": "Roll strategy applied: 'calendar', 'volume', or 'spread_optimal'"},
        "current_price": {"type": "float", "description": "Current market price of the position"},
        "qty": {"type": "int", "description": "Current position quantity"},
    },
    locales={
        "ko": {
            "name": "롤오버 관리 (Roll Management)",
            "description": "선물 계약의 만기까지 남은 일수를 모니터링하고 롤오버 신호를 생성합니다. 강제 청산을 방지하기 위한 최적 롤오버 타이밍을 제안합니다.",
            "fields.days_before_expiry": "만기 전 신호 발생 일수",
            "fields.roll_strategy": "롤오버 전략 (calendar: 달력 기반, volume: 거래량 기반, spread_optimal: 스프레드 최적)",
        },
    },
)

# 선물 월물 코드 매핑
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}

# 역매핑: 월 → 다음 월물 코드
NEXT_MONTH_CODE = {
    "F": "G", "G": "H", "H": "J", "J": "K", "K": "M", "M": "N",
    "N": "Q", "Q": "U", "U": "V", "V": "X", "X": "Z", "Z": "F",
}


def _parse_expiry_date(symbol: str) -> Optional[datetime]:
    """선물 심볼에서 대략적 만기일 추출 (매월 셋째 금요일 근사)"""
    if len(symbol) < 3:
        return None

    year_part = symbol[-2:]
    month_code = symbol[-3]

    if month_code not in MONTH_CODES:
        return None

    try:
        year = int(year_part) + 2000
        month = MONTH_CODES[month_code]

        # 셋째 금요일 근사: 해당 월 15~21일 중 금요일
        first_day = datetime(year, month, 1)
        # 첫 금요일 찾기
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        # 셋째 금요일
        third_friday = first_friday + timedelta(weeks=2)
        return third_friday
    except (ValueError, OverflowError):
        return None


def _get_next_contract(symbol: str) -> str:
    """다음 월물 심볼 생성"""
    if len(symbol) < 3:
        return symbol

    prefix = symbol[:-3]
    month_code = symbol[-3]
    year_part = symbol[-2:]

    next_month = NEXT_MONTH_CODE.get(month_code)
    if next_month is None:
        return symbol

    # Z→F 전환 시 연도 +1
    if month_code == "Z":
        try:
            next_year = int(year_part) + 1
            year_part = str(next_year).zfill(2)
        except ValueError:
            pass

    return f"{prefix}{next_month}{year_part}"


async def roll_management_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    """롤오버 관리 조건 평가"""
    if fields is None:
        fields = {}

    days_before_expiry = fields.get("days_before_expiry", 5)
    roll_strategy = fields.get("roll_strategy", "calendar")

    positions = positions or []
    if not positions:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    now = datetime.now()
    passed, failed, symbol_results = [], [], []

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")
        sym_dict = {"symbol": symbol, "exchange": exchange}

        expiry = _parse_expiry_date(symbol)
        if expiry is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "error": "Cannot parse expiry date",
            })
            continue

        days_to_expiry = (expiry - now).days
        should_roll = days_to_expiry <= days_before_expiry
        next_contract = _get_next_contract(symbol)

        result_info = {
            "symbol": symbol, "exchange": exchange,
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "days_to_expiry": days_to_expiry,
            "should_roll": should_roll,
            "next_contract": next_contract,
            "roll_strategy": roll_strategy,
            "current_price": pos_data.get("current_price", 0),
            "qty": pos_data.get("qty", pos_data.get("quantity", 0)),
        }

        # state 저장 (롤오버 이력)
        if should_roll and context and hasattr(context, "risk_tracker") and context.risk_tracker:
            try:
                await context.risk_tracker.set_state(
                    f"roll.{symbol}.signal_date",
                    now.strftime("%Y-%m-%d"),
                )
            except Exception:
                pass

        symbol_results.append(result_info)

        if should_roll:
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
            "indicator": "RollManagement",
            "days_before_expiry": days_before_expiry,
            "roll_strategy": roll_strategy,
            "total_positions": len(positions),
            "roll_needed": len(passed),
        },
    }


__all__ = ["roll_management_condition", "ROLL_MANAGEMENT_SCHEMA", "risk_features"]
