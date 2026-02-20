"""
MultiTimeframeConfirmation (다중 타임프레임 확인) 플러그인

단기/중기/장기 3개 기간의 추세 일치 여부 확인.
모든 타임프레임이 동일 방향일 때만 신호 발생하여 허위 신호 감소.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {short_period, medium_period, long_period, require_all, indicator}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MTF_CONFIRMATION_SCHEMA = PluginSchema(
    id="MultiTimeframeConfirmation",
    name="Multi-Timeframe Confirmation",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Evaluates trend direction across short/medium/long timeframes. Signals only when all timeframes agree, dramatically reducing false signals.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "short_period": {
            "type": "int",
            "default": 10,
            "title": "Short Period",
            "description": "Short-term MA period",
            "ge": 3,
            "le": 50,
        },
        "medium_period": {
            "type": "int",
            "default": 20,
            "title": "Medium Period",
            "description": "Medium-term MA period",
            "ge": 10,
            "le": 100,
        },
        "long_period": {
            "type": "int",
            "default": 50,
            "title": "Long Period",
            "description": "Long-term MA period",
            "ge": 20,
            "le": 200,
        },
        "require_all": {
            "type": "bool",
            "default": True,
            "title": "Require All Aligned",
            "description": "True: all 3 timeframes must agree. False: 2 of 3 is sufficient",
        },
        "direction": {
            "type": "string",
            "default": "bullish",
            "title": "Direction",
            "description": "bullish: uptrend confirmation, bearish: downtrend confirmation",
            "enum": ["bullish", "bearish"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["multi_timeframe", "confirmation", "trend", "filter"],
    locales={
        "ko": {
            "name": "다중 타임프레임 확인 (MTF Confirmation)",
            "description": "단기/중기/장기 3개 기간의 추세 방향이 일치하는지 확인합니다. 모든 기간이 같은 방향일 때만 신호를 발생시켜 허위 신호를 크게 줄입니다.",
            "fields.short_period": "단기 이동평균 기간",
            "fields.medium_period": "중기 이동평균 기간",
            "fields.long_period": "장기 이동평균 기간",
            "fields.require_all": "전체 일치 필요 (True: 3개 모두, False: 2/3 충분)",
            "fields.direction": "방향 (bullish: 상승 확인, bearish: 하락 확인)",
        },
    },
)


def _sma(prices: List[float], period: int) -> Optional[float]:
    """단순 이동평균 (마지막 값)"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


async def multi_timeframe_confirmation_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """다중 타임프레임 확인 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    short_period = fields.get("short_period", 10)
    medium_period = fields.get("medium_period", 20)
    long_period = fields.get("long_period", 50)
    require_all = fields.get("require_all", True)
    direction = fields.get("direction", "bullish")

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

    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in symbol_data_map]

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        if len(prices) < long_period + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_price = prices[-1]
        short_ma = _sma(prices, short_period)
        medium_ma = _sma(prices, medium_period)
        long_ma = _sma(prices, long_period)

        if short_ma is None or medium_ma is None or long_ma is None:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "MA calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 각 타임프레임의 추세 판단
        if direction == "bullish":
            short_aligned = current_price > short_ma
            medium_aligned = current_price > medium_ma
            long_aligned = current_price > long_ma
        else:
            short_aligned = current_price < short_ma
            medium_aligned = current_price < medium_ma
            long_aligned = current_price < long_ma

        aligned_count = sum([short_aligned, medium_aligned, long_aligned])

        if require_all:
            passed_condition = aligned_count == 3
        else:
            passed_condition = aligned_count >= 2

        alignment = f"{aligned_count}/3"

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "short_ma": round(short_ma, 2), "medium_ma": round(medium_ma, 2), "long_ma": round(long_ma, 2),
            "current_price": current_price,
            "short_aligned": short_aligned, "medium_aligned": medium_aligned, "long_aligned": long_aligned,
            "alignment": alignment, "confirmed": passed_condition,
        })

        # time_series
        time_series = []
        if rows_sorted:
            last_row = rows_sorted[-1]
            signal = "buy" if passed_condition and direction == "bullish" else ("sell" if passed_condition and direction == "bearish" else None)
            time_series.append({
                date_field: last_row.get(date_field, ""),
                close_field: current_price,
                "short_ma": round(short_ma, 2),
                "medium_ma": round(medium_ma, 2),
                "long_ma": round(long_ma, 2),
                "alignment": alignment,
                "signal": signal,
                "side": "long",
            })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "MultiTimeframeConfirmation",
            "short_period": short_period, "medium_period": medium_period, "long_period": long_period,
            "require_all": require_all, "direction": direction,
        },
    }


__all__ = ["multi_timeframe_confirmation_condition", "MTF_CONFIRMATION_SCHEMA"]
