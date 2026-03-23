"""
Seasonal Filter (계절성 필터) 플러그인

Bouman & Jacobsen (2002) "The Halloween Indicator, Sell in May and Go Away".
Halloween 효과: 11월~4월 보유, 5월~10월 회피.
37개 시장 중 36개에서 통계적으로 유의미한 효과 확인.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {strategy, buy_months, sell_months, transition_mode, hemisphere}

특이사항: 가격이 아닌 날짜 기반 판단.
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SEASONAL_FILTER_SCHEMA = PluginSchema(
    id="SeasonalFilter",
    name="Seasonal Filter",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Date-based seasonal filter based on the Halloween Effect (Bouman & Jacobsen 2002). Hold during November-April (strong season), avoid May-October (weak season). Supports custom month ranges and Southern Hemisphere adjustment.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "strategy": {
            "type": "string",
            "default": "halloween",
            "title": "Strategy",
            "description": "halloween: Nov-Apr buy / May-Oct sell. custom: use buy_months/sell_months",
            "enum": ["halloween", "custom"],
        },
        "buy_months": {
            "type": "string",
            "default": "11,12,1,2,3,4",
            "title": "Buy Months",
            "description": "Months to hold (comma-separated, 1-12). Used when strategy=custom",
        },
        "sell_months": {
            "type": "string",
            "default": "5,6,7,8,9,10",
            "title": "Sell Months",
            "description": "Months to avoid (comma-separated, 1-12). Used when strategy=custom",
        },
        "transition_mode": {
            "type": "string",
            "default": "strict",
            "title": "Transition Mode",
            "description": "strict: switch immediately on month change, gradual: annotated transition period",
            "enum": ["strict", "gradual"],
        },
        "hemisphere": {
            "type": "string",
            "default": "northern",
            "title": "Hemisphere",
            "description": "northern: standard, southern: 6-month shift for Australia, Brazil, etc.",
            "enum": ["northern", "southern"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["seasonal", "halloween", "sell-in-may", "calendar", "bouman"],
    output_fields={
        "seasonal_signal": {"type": "str", "description": "Seasonal signal: 'buy_period', 'sell_period', or 'unknown'"},
        "current_month": {"type": "int", "description": "Current month number (1–12)"},
        "days_to_transition": {"type": "int", "description": "Days until the next seasonal transition"},
    },
    locales={
        "ko": {
            "name": "계절성 필터",
            "description": "핼로윈 효과 기반 계절성 필터 (Bouman & Jacobsen 2002). 11~4월 보유, 5~10월 회피. 37개 시장 중 36개에서 통계적으로 검증된 효과입니다.",
            "fields.strategy": "전략 (halloween: 핼로윈 효과, custom: 직접 지정)",
            "fields.buy_months": "보유 월 (쉼표 구분, 1-12)",
            "fields.sell_months": "회피 월 (쉼표 구분, 1-12)",
            "fields.transition_mode": "전환 방식 (strict: 즉시, gradual: 점진적)",
            "fields.hemisphere": "반구 (northern: 북반구, southern: 남반구 6개월 시프트)",
        },
    },
)

# Halloween 기본 설정
HALLOWEEN_BUY_MONTHS = {11, 12, 1, 2, 3, 4}
HALLOWEEN_SELL_MONTHS = {5, 6, 7, 8, 9, 10}


def _parse_months(months_str: str) -> set:
    """쉼표로 구분된 월 문자열 파싱"""
    if not months_str:
        return set()
    result = set()
    for m in str(months_str).split(","):
        m = m.strip()
        if m.isdigit():
            month = int(m)
            if 1 <= month <= 12:
                result.add(month)
    return result


def _parse_date(date_str: str) -> Optional[tuple]:
    """날짜 파싱 → (year, month, day)"""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        if "-" in date_str:
            parts = date_str.split("-")
            if len(parts) >= 3:
                return int(parts[0]), int(parts[1]), int(parts[2][:2])
        elif len(date_str) >= 8:
            return int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
    except (ValueError, IndexError):
        pass
    return None


def _shift_month_south(month: int) -> int:
    """남반구 계절 시프트 (+6개월)"""
    return ((month - 1 + 6) % 12) + 1


def _days_in_month(year: int, month: int) -> int:
    """해당 월의 일수"""
    days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        return 29
    return days[month]


def _days_to_transition(year: int, month: int, day: int, buy_months: set) -> int:
    """다음 전환까지 남은 일수"""
    current_in_buy = month in buy_months
    remaining_in_month = _days_in_month(year, month) - day

    total = remaining_in_month
    check_month = month
    check_year = year

    for _ in range(12):
        check_month = check_month % 12 + 1
        if check_month == 1:
            check_year += 1
        next_in_buy = check_month in buy_months
        if next_in_buy != current_in_buy:
            return total
        total += _days_in_month(check_year, check_month)

    return 0


async def seasonal_filter_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """계절성 필터 조건 평가"""
    mapping = field_mapping or {}
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    close_field = mapping.get("close_field", "close")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    strategy = fields.get("strategy", "halloween")
    hemisphere = fields.get("hemisphere", "northern")

    # 매수/매도 월 결정
    if strategy == "halloween":
        buy_months = HALLOWEEN_BUY_MONTHS.copy()
        sell_months = HALLOWEEN_SELL_MONTHS.copy()
    else:
        buy_months = _parse_months(fields.get("buy_months", "11,12,1,2,3,4"))
        sell_months = _parse_months(fields.get("sell_months", "5,6,7,8,9,10"))

    # 남반구 시프트
    if hemisphere == "southern":
        buy_months = {_shift_month_south(m) for m in buy_months}
        sell_months = {_shift_month_south(m) for m in sell_months}

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    # 종목별 데이터 그룹화
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

    if symbols:
        target_symbols = [
            {"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")}
            if isinstance(s, dict) else {"symbol": str(s), "exchange": "UNKNOWN"}
            for s in symbols
        ]
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "seasonal_signal": "unknown", "current_month": None,
                "error": "No data provided",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        # 최신 날짜 파싱
        latest_row = rows_sorted[-1]
        date_parsed = _parse_date(str(latest_row.get(date_field, "")))

        if date_parsed is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "seasonal_signal": "unknown", "current_month": None,
                "error": "Cannot parse date",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        year, month, day = date_parsed

        # 현재 월 신호 판단
        if month in buy_months:
            seasonal_signal = "buy_period"
        elif month in sell_months:
            seasonal_signal = "sell_period"
        else:
            seasonal_signal = "neutral"

        # 다음 전환까지 일수
        days_to_next = _days_to_transition(year, month, day, buy_months)

        # 시계열 생성
        time_series = []
        for row in rows_sorted:
            row_date = _parse_date(str(row.get(date_field, "")))
            if row_date:
                r_year, r_month, r_day = row_date
                r_month_effective = _shift_month_south(r_month) if hemisphere == "southern" else r_month
                if r_month_effective in buy_months:
                    r_signal = "buy_period"
                elif r_month_effective in sell_months:
                    r_signal = "sell_period"
                else:
                    r_signal = "neutral"
            else:
                r_signal = "unknown"

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "seasonal_signal": r_signal,
                "current_month": row_date[1] if row_date else None,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "seasonal_signal": seasonal_signal,
            "current_month": month,
            "days_to_transition": days_to_next,
        })

        # buy_period이면 통과
        passed_condition = seasonal_signal == "buy_period"
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "SeasonalFilter",
            "strategy": strategy,
            "hemisphere": hemisphere,
            "buy_months": sorted(list(buy_months)),
            "sell_months": sorted(list(sell_months)),
        },
    }


__all__ = [
    "seasonal_filter_condition",
    "_parse_months",
    "_parse_date",
    "_days_to_transition",
    "SEASONAL_FILTER_SCHEMA",
]
