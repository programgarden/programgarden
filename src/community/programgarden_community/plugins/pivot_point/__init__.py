"""
Pivot Point (피봇 포인트) 플러그인

전일 고가/저가/종가를 이용하여 당일의 지지/저항 레벨을 계산합니다.
- Standard: PP = (H+L+C)/3 기반
- Fibonacci: PP에 피보나치 비율 적용
- Camarilla: 레인지 기반 계산

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {pivot_type, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PIVOT_POINT_SCHEMA = PluginSchema(
    id="PivotPoint",
    name="Pivot Point",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Calculates support and resistance levels using pivot points from previous day's high, low, and close. Supports Standard, Fibonacci, and Camarilla methods. Price near support levels suggests buying, near resistance suggests selling.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "pivot_type": {
            "type": "string",
            "default": "standard",
            "title": "Pivot Type",
            "description": "Pivot calculation method",
            "enum": ["standard", "fibonacci", "camarilla"],
        },
        "direction": {
            "type": "string",
            "default": "support",
            "title": "Direction",
            "description": "support: buy near support levels, resistance: sell near resistance levels",
            "enum": ["support", "resistance"],
        },
        "tolerance": {
            "type": "float",
            "default": 0.01,
            "title": "Tolerance",
            "description": "Tolerance for level proximity (as percentage)",
            "ge": 0.002,
            "le": 0.05,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["pivot", "support", "resistance", "price_level"],
    output_fields={
        "pivot_type": {"type": "str", "description": "Pivot calculation method used (standard/fibonacci/camarilla)"},
        "pp": {"type": "float", "description": "Pivot point level"},
        "r1": {"type": "float", "description": "First resistance level"},
        "r2": {"type": "float", "description": "Second resistance level"},
        "r3": {"type": "float", "description": "Third resistance level"},
        "s1": {"type": "float", "description": "First support level"},
        "s2": {"type": "float", "description": "Second support level"},
        "s3": {"type": "float", "description": "Third support level"},
        "current_price": {"type": "float", "description": "Current close price"},
        "nearest_level": {"type": "str", "description": "Name of the nearest pivot level"},
        "nearest_price": {"type": "float", "description": "Price of the nearest pivot level"},
        "distance_pct": {"type": "float", "description": "Distance from current price to nearest level (%)"},
    },
    locales={
        "ko": {
            "name": "피봇 포인트",
            "description": "전일 고가/저가/종가를 이용하여 당일의 지지/저항 레벨을 계산합니다. Standard, Fibonacci, Camarilla 3가지 방식을 지원합니다. 가격이 지지선 근처이면 매수, 저항선 근처이면 매도 기회입니다.",
            "fields.pivot_type": "계산 방식 (standard, fibonacci, camarilla)",
            "fields.direction": "방향 (support: 지지선 매수, resistance: 저항선 매도)",
            "fields.tolerance": "레벨 근접 허용 범위 (퍼센트)",
        },
    },
)


def calculate_pivot_standard(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Standard 피봇 포인트 계산

    PP = (H + L + C) / 3
    S1 = 2*PP - H, R1 = 2*PP - L
    S2 = PP - (H - L), R2 = PP + (H - L)
    S3 = L - 2*(H - PP), R3 = H + 2*(PP - L)
    """
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)

    return {
        "pp": round(pp, 4),
        "r1": round(r1, 4),
        "r2": round(r2, 4),
        "r3": round(r3, 4),
        "s1": round(s1, 4),
        "s2": round(s2, 4),
        "s3": round(s3, 4),
    }


def calculate_pivot_fibonacci(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Fibonacci 피봇 포인트 계산

    PP = (H + L + C) / 3
    R1 = PP + 0.382 * (H - L), S1 = PP - 0.382 * (H - L)
    R2 = PP + 0.618 * (H - L), S2 = PP - 0.618 * (H - L)
    R3 = PP + 1.000 * (H - L), S3 = PP - 1.000 * (H - L)
    """
    pp = (high + low + close) / 3
    diff = high - low

    r1 = pp + 0.382 * diff
    s1 = pp - 0.382 * diff
    r2 = pp + 0.618 * diff
    s2 = pp - 0.618 * diff
    r3 = pp + 1.0 * diff
    s3 = pp - 1.0 * diff

    return {
        "pp": round(pp, 4),
        "r1": round(r1, 4),
        "r2": round(r2, 4),
        "r3": round(r3, 4),
        "s1": round(s1, 4),
        "s2": round(s2, 4),
        "s3": round(s3, 4),
    }


def calculate_pivot_camarilla(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Camarilla 피봇 포인트 계산

    PP = (H + L + C) / 3
    R1 = C + (H - L) * 1.1/12, S1 = C - (H - L) * 1.1/12
    R2 = C + (H - L) * 1.1/6,  S2 = C - (H - L) * 1.1/6
    R3 = C + (H - L) * 1.1/4,  S3 = C - (H - L) * 1.1/4
    """
    pp = (high + low + close) / 3
    diff = high - low

    r1 = close + diff * 1.1 / 12
    s1 = close - diff * 1.1 / 12
    r2 = close + diff * 1.1 / 6
    s2 = close - diff * 1.1 / 6
    r3 = close + diff * 1.1 / 4
    s3 = close - diff * 1.1 / 4

    return {
        "pp": round(pp, 4),
        "r1": round(r1, 4),
        "r2": round(r2, 4),
        "r3": round(r3, 4),
        "s1": round(s1, 4),
        "s2": round(s2, 4),
        "s3": round(s3, 4),
    }


PIVOT_CALCULATORS = {
    "standard": calculate_pivot_standard,
    "fibonacci": calculate_pivot_fibonacci,
    "camarilla": calculate_pivot_camarilla,
}


def find_nearest_level(
    current_price: float,
    pivot_levels: Dict[str, float],
    direction: str,
) -> Dict[str, Any]:
    """
    현재 가격에서 가장 가까운 레벨 찾기

    Args:
        current_price: 현재 가격
        pivot_levels: 피봇 레벨 딕셔너리
        direction: "support" or "resistance"

    Returns:
        {level_name, level_price, distance_pct}
    """
    if direction == "support":
        # 지지: 현재가 아래의 레벨 중 가장 가까운 것
        candidates = {k: v for k, v in pivot_levels.items() if v <= current_price and k != "pp"}
        if not candidates:
            candidates = {"pp": pivot_levels["pp"]}
    else:
        # 저항: 현재가 위의 레벨 중 가장 가까운 것
        candidates = {k: v for k, v in pivot_levels.items() if v >= current_price and k != "pp"}
        if not candidates:
            candidates = {"pp": pivot_levels["pp"]}

    nearest_name = min(candidates, key=lambda k: abs(candidates[k] - current_price))
    nearest_price = candidates[nearest_name]
    distance_pct = abs(current_price - nearest_price) / nearest_price * 100 if nearest_price > 0 else 0

    return {
        "level_name": nearest_name,
        "level_price": nearest_price,
        "distance_pct": round(distance_pct, 2),
    }


async def pivot_point_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Pivot Point 조건 평가
    """
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    pivot_type = fields.get("pivot_type", "standard")
    direction = fields.get("direction", "support")
    tolerance = fields.get("tolerance", 0.01)

    calculator = PIVOT_CALCULATORS.get(pivot_type, calculate_pivot_standard)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
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

    # 평가할 종목 결정
    if symbols:
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({
                    "symbol": s.get("symbol", ""),
                    "exchange": s.get("exchange", "UNKNOWN"),
                })
            else:
                target_symbols.append({"symbol": str(s), "exchange": "UNKNOWN"})
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed = []
    failed = []
    symbol_results = []
    values = []

    min_required = 2  # 최소 2일 (전일 + 당일)

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "pivot": None,
                "nearest_level": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        if len(rows_sorted) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "pivot": None,
                "nearest_level": None,
                "error": f"Insufficient data: need {min_required}, got {len(rows_sorted)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # time_series 생성: 각 날짜별로 전일 HLC 기반 피봇 계산
        time_series = []

        for i in range(1, len(rows_sorted)):
            prev_row = rows_sorted[i - 1]
            current_row = rows_sorted[i]

            try:
                prev_high = float(prev_row.get(high_field, 0))
                prev_low = float(prev_row.get(low_field, 0))
                prev_close = float(prev_row.get(close_field, 0))
                current_close = float(current_row.get(close_field, 0))
            except (ValueError, TypeError):
                continue

            if prev_high <= 0 or prev_low <= 0:
                continue

            pivot_levels = calculator(prev_high, prev_low, prev_close)
            nearest = find_nearest_level(current_close, pivot_levels, direction)

            signal = None
            side = "long"

            if nearest["distance_pct"] / 100 <= tolerance:
                if direction == "support":
                    signal = "buy"
                else:
                    signal = "sell"

            time_series.append({
                date_field: current_row.get(date_field, ""),
                open_field: current_row.get(open_field),
                high_field: current_row.get(high_field),
                low_field: current_row.get(low_field),
                close_field: current_row.get(close_field),
                volume_field: current_row.get(volume_field),
                "pp": pivot_levels["pp"],
                "r1": pivot_levels["r1"],
                "r2": pivot_levels["r2"],
                "r3": pivot_levels["r3"],
                "s1": pivot_levels["s1"],
                "s2": pivot_levels["s2"],
                "s3": pivot_levels["s3"],
                "nearest_level": nearest["level_name"],
                "nearest_price": nearest["level_price"],
                "distance_pct": nearest["distance_pct"],
                "signal": signal,
                "side": side,
            })

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        # 마지막 날의 피봇 결과
        if time_series:
            last_entry = time_series[-1]
            current_close_val = float(rows_sorted[-1].get(close_field, 0))

            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "pivot_type": pivot_type,
                "pp": last_entry["pp"],
                "r1": last_entry["r1"],
                "r2": last_entry["r2"],
                "r3": last_entry["r3"],
                "s1": last_entry["s1"],
                "s2": last_entry["s2"],
                "s3": last_entry["s3"],
                "current_price": current_close_val,
                "nearest_level": last_entry["nearest_level"],
                "nearest_price": last_entry["nearest_price"],
                "distance_pct": last_entry["distance_pct"],
            })

            # 조건 평가: 가장 가까운 레벨이 tolerance 이내
            passed_condition = last_entry["distance_pct"] / 100 <= tolerance
        else:
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "pivot_type": pivot_type,
                "pp": None,
                "nearest_level": None,
                "error": "Calculation failed",
            })
            passed_condition = False

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "PivotPoint",
            "pivot_type": pivot_type,
            "direction": direction,
            "tolerance": tolerance,
        },
    }


__all__ = [
    "pivot_point_condition",
    "calculate_pivot_standard",
    "calculate_pivot_fibonacci",
    "calculate_pivot_camarilla",
    "find_nearest_level",
    "PIVOT_POINT_SCHEMA",
]
