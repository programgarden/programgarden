"""
CalendarSpread (캘린더 스프레드) 플러그인 - 선물 전용

선물 월물 간 스프레드의 평균회귀 또는 모멘텀 매매 신호 생성.

입력 형식:
- data: 플랫 배열 (2개 월물의 시계열 데이터 포함)
  [{symbol: "CLF26", date: "20260116", close: 70.5, ...},
   {symbol: "CLG26", date: "20260116", close: 71.2, ...}, ...]
- fields: {spread_ma_period, entry_deviation, exit_deviation, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CALENDAR_SPREAD_SCHEMA = PluginSchema(
    id="CalendarSpread",
    name="Calendar Spread",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Monitors and trades the price spread between two futures contract months. Generates signals when spread reaches extremes for mean-reversion or momentum trades.",
    products=[ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "spread_ma_period": {
            "type": "int",
            "default": 20,
            "title": "Spread MA Period",
            "description": "Moving average period for spread normalization",
            "ge": 5,
            "le": 100,
        },
        "entry_deviation": {
            "type": "float",
            "default": 2.0,
            "title": "Entry Deviation (σ)",
            "description": "Standard deviation multiple for entry signal",
            "ge": 0.5,
            "le": 5.0,
        },
        "exit_deviation": {
            "type": "float",
            "default": 0.5,
            "title": "Exit Deviation (σ)",
            "description": "Standard deviation multiple for exit signal",
            "ge": 0.0,
            "le": 3.0,
        },
        "strategy": {
            "type": "string",
            "default": "mean_revert",
            "title": "Strategy",
            "description": "mean_revert: trade spread back to mean, momentum: trade spread continuation",
            "enum": ["mean_revert", "momentum"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["futures", "calendar_spread", "spread_trading", "mean_reversion"],
    output_fields={
        "role": {"type": "str", "description": "Contract role: 'front_month' or 'back_month'"},
        "price": {"type": "float", "description": "Latest close price of this contract"},
        "spread": {"type": "float", "description": "Current spread value (back minus front price)"},
        "spread_ma": {"type": "float", "description": "Moving average of the spread"},
        "z_score": {"type": "float", "description": "Z-Score of the current spread relative to its mean"},
        "signal": {"type": "str", "description": "Trading signal: 'buy', 'sell', 'exit', or None"},
    },
    locales={
        "ko": {
            "name": "캘린더 스프레드 (Calendar Spread)",
            "description": "선물 2개 월물 간 가격 스프레드를 추적하여, 스프레드가 극단값에 도달하면 매매 신호를 생성합니다. 평균회귀 또는 모멘텀 전략을 선택할 수 있습니다.",
            "fields.spread_ma_period": "스프레드 이동평균 기간",
            "fields.entry_deviation": "진입 시그널 표준편차 배수",
            "fields.exit_deviation": "청산 시그널 표준편차 배수",
            "fields.strategy": "전략 (mean_revert: 평균회귀, momentum: 모멘텀)",
        },
    },
)

# 선물 월물 코드 매핑
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


def _parse_contract_order(symbol: str) -> Optional[int]:
    """선물 심볼에서 만기 순서 추출"""
    if len(symbol) < 3:
        return None
    year_part = symbol[-2:]
    month_code = symbol[-3]
    if month_code not in MONTH_CODES:
        return None
    try:
        year = int(year_part) + 2000
        month = MONTH_CODES[month_code]
        return year * 100 + month
    except ValueError:
        return None


async def calendar_spread_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """캘린더 스프레드 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    spread_ma_period = fields.get("spread_ma_period", 20)
    entry_deviation = fields.get("entry_deviation", 2.0)
    exit_deviation = fields.get("exit_deviation", 0.5)
    strategy = fields.get("strategy", "mean_revert")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
        }

    # 종목별 그룹화
    symbol_data_map: Dict[str, List[Dict]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        if sym not in symbol_data_map:
            symbol_data_map[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        symbol_data_map[sym].append(row)

    # 만기 순서로 정렬하여 근월물/원월물 결정
    contract_orders = []
    for sym in symbol_data_map:
        order = _parse_contract_order(sym)
        if order is not None:
            contract_orders.append((sym, order))

    contract_orders.sort(key=lambda x: x[1])

    if len(contract_orders) < 2:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "Need at least 2 futures contracts for calendar spread"},
        }

    front_sym = contract_orders[0][0]
    back_sym = contract_orders[1][0]

    # 날짜별 가격 맵
    front_prices: Dict[str, float] = {}
    for row in symbol_data_map[front_sym]:
        date = row.get(date_field, "")
        price = row.get(close_field)
        if date and price is not None:
            try:
                front_prices[date] = float(price)
            except (ValueError, TypeError):
                pass

    back_prices: Dict[str, float] = {}
    for row in symbol_data_map[back_sym]:
        date = row.get(date_field, "")
        price = row.get(close_field)
        if date and price is not None:
            try:
                back_prices[date] = float(price)
            except (ValueError, TypeError):
                pass

    # 공통 날짜의 스프레드 시계열
    common_dates = sorted(set(front_prices.keys()) & set(back_prices.keys()))
    if len(common_dates) < spread_ma_period:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": f"Insufficient common dates ({len(common_dates)}) for spread MA period ({spread_ma_period})"},
        }

    spreads = [back_prices[d] - front_prices[d] for d in common_dates]

    # 스프레드 이동평균/표준편차
    recent_spreads = spreads[-spread_ma_period:]
    spread_ma = sum(recent_spreads) / len(recent_spreads)
    spread_std = (sum((s - spread_ma) ** 2 for s in recent_spreads) / len(recent_spreads)) ** 0.5

    current_spread = spreads[-1]
    z_score = (current_spread - spread_ma) / spread_std if spread_std > 0 else 0
    z_score = round(z_score, 2)

    # 신호 판단
    if strategy == "mean_revert":
        if z_score > entry_deviation:
            signal = "sell"  # 스프레드가 높으면 근월물 매수, 원월물 매도
        elif z_score < -entry_deviation:
            signal = "buy"  # 스프레드가 낮으면 근월물 매도, 원월물 매수
        elif abs(z_score) < exit_deviation:
            signal = "exit"
        else:
            signal = None
    else:  # momentum
        if z_score > entry_deviation:
            signal = "buy"  # 스프레드 확대 추세 따라가기
        elif z_score < -entry_deviation:
            signal = "sell"  # 스프레드 축소 추세 따라가기
        else:
            signal = None

    has_signal = signal is not None and signal != "exit"

    # 결과
    passed, failed, symbol_results, values = [], [], [], []

    for sym in [front_sym, back_sym]:
        exchange = symbol_exchange_map.get(sym, "UNKNOWN")
        sym_dict = {"symbol": sym, "exchange": exchange}

        if has_signal:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        is_front = sym == front_sym
        symbol_results.append({
            "symbol": sym, "exchange": exchange,
            "role": "front_month" if is_front else "back_month",
            "price": front_prices.get(common_dates[-1], 0) if is_front else back_prices.get(common_dates[-1], 0),
            "spread": round(current_spread, 4),
            "spread_ma": round(spread_ma, 4),
            "z_score": z_score,
            "signal": signal,
        })

    # time_series (스프레드 이력)
    time_series = []
    start_idx = max(0, len(common_dates) - spread_ma_period)
    for i in range(start_idx, len(common_dates)):
        date = common_dates[i]
        time_series.append({
            date_field: date,
            "spread": round(spreads[i], 4),
            "front_price": front_prices[date],
            "back_price": back_prices[date],
        })

    if time_series:
        time_series[-1]["z_score"] = z_score
        time_series[-1]["signal"] = signal
        time_series[-1]["side"] = "long"

    values.append({
        "symbol": f"{front_sym}-{back_sym}",
        "exchange": symbol_exchange_map.get(front_sym, "UNKNOWN"),
        "time_series": time_series,
    })

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "spread_info": {
            "front_month": front_sym, "back_month": back_sym,
            "current_spread": round(current_spread, 4),
            "spread_ma": round(spread_ma, 4),
            "spread_std": round(spread_std, 4),
            "z_score": z_score,
        },
        "analysis": {
            "indicator": "CalendarSpread",
            "spread_ma_period": spread_ma_period,
            "entry_deviation": entry_deviation, "exit_deviation": exit_deviation,
            "strategy": strategy,
        },
    }


__all__ = ["calendar_spread_condition", "CALENDAR_SPREAD_SCHEMA"]
