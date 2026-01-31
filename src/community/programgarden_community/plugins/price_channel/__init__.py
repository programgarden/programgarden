"""
Price Channel (Donchian Channel) 플러그인

N일간 최고가/최저가로 채널을 형성하여 돌파 신호를 생성합니다.
- 상단 채널 돌파: 강한 상승 모멘텀 (매수 신호)
- 하단 채널 이탈: 강한 하락 모멘텀 (매도 신호)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {period, direction}
- field_mapping: {high_field, low_field, close_field, ...}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PRICE_CHANNEL_SCHEMA = PluginSchema(
    id="PriceChannel",
    name="Price Channel (Donchian)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies breakouts using Donchian Channels. Upper channel is N-day highest high, lower channel is N-day lowest low. Buy signal on upper breakout, sell signal on lower breakout.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "Channel Period",
            "description": "Period for channel calculation (N-day high/low)",
            "ge": 5,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "breakout_high",
            "title": "Direction",
            "description": "breakout_high: buy signal on upper breakout, breakout_low: sell signal on lower breakout",
            "enum": ["breakout_high", "breakout_low"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["trend", "breakout", "channel"],
    locales={
        "ko": {
            "name": "가격 채널 (돈치안)",
            "description": "돈치안 채널을 이용해 돌파 신호를 생성합니다. 상단 채널은 N일 최고가, 하단 채널은 N일 최저가입니다. 상단 돌파 시 매수 신호, 하단 이탈 시 매도 신호입니다.",
            "fields.period": "채널 계산 기간 (N일 최고/최저)",
            "fields.direction": "방향 (breakout_high: 상단 돌파 매수, breakout_low: 하단 이탈 매도)",
        },
    },
)


def calculate_channel(highs: List[float], lows: List[float], period: int = 20) -> Dict[str, float]:
    """
    Donchian Channel 계산

    Args:
        highs: 고가 배열
        lows: 저가 배열
        period: 채널 기간

    Returns:
        {"upper": float, "lower": float, "middle": float}
    """
    if len(highs) < period or len(lows) < period:
        return {"upper": 0.0, "lower": 0.0, "middle": 0.0}

    upper = max(highs[-period:])
    lower = min(lows[-period:])
    middle = (upper + lower) / 2

    return {
        "upper": round(upper, 4),
        "lower": round(lower, 4),
        "middle": round(middle, 4),
    }


def calculate_channel_series(
    highs: List[float],
    lows: List[float],
    period: int = 20
) -> List[Dict[str, float]]:
    """
    Donchian Channel 시계열 계산

    Note: 현재 봉을 제외한 이전 N일의 최고/최저를 사용하여
    현재 가격이 채널 돌파 여부를 판단할 수 있도록 합니다.

    Returns:
        [{"upper": float, "lower": float, "middle": float}, ...]
    """
    if len(highs) < period + 1:  # 최소 period+1일 필요 (현재 봉 제외)
        return []

    results = []
    # i번째 봉에 대해, i-period ~ i-1 범위의 최고/최저로 채널 계산
    for i in range(period, len(highs)):
        sub_highs = highs[i - period:i]  # 현재 봉 제외, 이전 N일
        sub_lows = lows[i - period:i]

        upper = max(sub_highs)
        lower = min(sub_lows)
        middle = (upper + lower) / 2

        results.append({
            "upper": round(upper, 4),
            "lower": round(lower, 4),
            "middle": round(middle, 4),
        })

    return results


async def price_channel_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Price Channel 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {period, direction}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        {passed_symbols, failed_symbols, symbol_results, values, result}
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

    period = fields.get("period", 20)
    direction = fields.get("direction", "breakout_high")

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

    min_required = period

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
                "upper_channel": None,
                "lower_channel": None,
                "middle_channel": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs = []
        lows = []
        closes = []

        for row in rows_sorted:
            try:
                h = float(row.get(high_field, 0))
                l = float(row.get(low_field, 0))
                c = float(row.get(close_field, 0))
                highs.append(h)
                lows.append(l)
                closes.append(c)
            except (ValueError, TypeError):
                pass

        if len(highs) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "upper_channel": None,
                "lower_channel": None,
                "middle_channel": None,
                "error": f"Insufficient data: need {min_required}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 채널 계산
        channel_series = calculate_channel_series(highs, lows, period)

        if not channel_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "upper_channel": None,
                "lower_channel": None,
                "middle_channel": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_channel = channel_series[-1]
        current_close = closes[-1]
        upper_channel = current_channel["upper"]
        lower_channel = current_channel["lower"]
        middle_channel = current_channel["middle"]

        # time_series 생성
        channel_start_idx = period - 1
        time_series = []

        for i, channel_val in enumerate(channel_series):
            row_idx = channel_start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]
                close_price = closes[row_idx]

                signal = None
                side = "long"

                # 돌파 감지
                if close_price > channel_val["upper"]:
                    signal = "buy"
                    side = "long"
                elif close_price < channel_val["lower"]:
                    signal = "sell"
                    side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "upper_channel": channel_val["upper"],
                    "lower_channel": channel_val["lower"],
                    "middle_channel": channel_val["middle"],
                    "signal": signal,
                    "side": side,
                })

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "upper_channel": upper_channel,
            "lower_channel": lower_channel,
            "middle_channel": middle_channel,
            "current_price": current_close,
        })

        # 조건 평가
        if direction == "breakout_high":
            passed_condition = current_close > upper_channel
        else:  # breakout_low
            passed_condition = current_close < lower_channel

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
            "indicator": "PriceChannel",
            "period": period,
            "direction": direction,
        },
    }


__all__ = ["price_channel_condition", "calculate_channel", "calculate_channel_series", "PRICE_CHANNEL_SCHEMA"]
