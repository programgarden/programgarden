"""
HeikinAshi (하이킨아시) 플러그인

노이즈 제거 캔들 변환 + 연속 양봉/음봉 기반 추세 신호.
HA 캔들은 추세를 시각적으로 명확하게 보여줍니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {consecutive_count, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


HEIKIN_ASHI_SCHEMA = PluginSchema(
    id="HeikinAshi",
    name="Heikin-Ashi",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Heikin-Ashi candle transformation for noise reduction. Detects trends by consecutive bullish/bearish HA candles and reversal patterns.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "consecutive_count": {
            "type": "int",
            "default": 3,
            "title": "Consecutive Count",
            "description": "Minimum consecutive candles for trend signal",
            "ge": 1,
            "le": 10,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish",
            "title": "Signal Type",
            "description": "Type of Heikin-Ashi signal",
            "enum": ["bullish", "bearish", "reversal_up", "reversal_down"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["heikin-ashi", "candle", "trend", "noise-reduction"],
    output_fields={
        "ha_open": {"type": "float", "description": "Heikin-Ashi open price"},
        "ha_close": {"type": "float", "description": "Heikin-Ashi close price"},
        "ha_high": {"type": "float", "description": "Heikin-Ashi high price"},
        "ha_low": {"type": "float", "description": "Heikin-Ashi low price"},
        "consecutive_bullish": {"type": "int", "description": "Count of consecutive bullish HA candles"},
        "consecutive_bearish": {"type": "int", "description": "Count of consecutive bearish HA candles"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "하이킨아시",
            "description": "하이킨아시 캔들 변환으로 노이즈를 제거합니다. 연속 양봉/음봉 수로 추세를 판단하고 반전 패턴을 감지합니다.",
            "fields.consecutive_count": "추세 신호 최소 연속 캔들 수",
            "fields.signal_type": "신호 유형 (상승, 하락, 상방반전, 하방반전)",
        },
    },
)


def calculate_heikin_ashi(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
) -> List[Dict[str, Any]]:
    """Heikin-Ashi 캔들 시계열 계산"""
    n = len(closes)
    if n == 0 or n != len(opens) or n != len(highs) or n != len(lows):
        return []

    result = []
    ha_open = (opens[0] + closes[0]) / 2
    ha_close = (opens[0] + highs[0] + lows[0] + closes[0]) / 4
    ha_high = max(highs[0], ha_open, ha_close)
    ha_low = min(lows[0], ha_open, ha_close)

    consec_bull = 1 if ha_close > ha_open else 0
    consec_bear = 1 if ha_close < ha_open else 0

    result.append({
        "ha_open": round(ha_open, 4),
        "ha_close": round(ha_close, 4),
        "ha_high": round(ha_high, 4),
        "ha_low": round(ha_low, 4),
        "consecutive_bullish": consec_bull,
        "consecutive_bearish": consec_bear,
    })

    for i in range(1, n):
        prev_ha_open = ha_open
        prev_ha_close = ha_close

        ha_close = (opens[i] + highs[i] + lows[i] + closes[i]) / 4
        ha_open = (prev_ha_open + prev_ha_close) / 2
        ha_high = max(highs[i], ha_open, ha_close)
        ha_low = min(lows[i], ha_open, ha_close)

        if ha_close > ha_open:
            consec_bull += 1
            consec_bear = 0
        elif ha_close < ha_open:
            consec_bear += 1
            consec_bull = 0
        else:
            consec_bull = 0
            consec_bear = 0

        result.append({
            "ha_open": round(ha_open, 4),
            "ha_close": round(ha_close, 4),
            "ha_high": round(ha_high, 4),
            "ha_low": round(ha_low, 4),
            "consecutive_bullish": consec_bull,
            "consecutive_bearish": consec_bear,
        })

    return result


async def heikin_ashi_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Heikin-Ashi 조건 평가"""
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    consecutive_count = fields.get("consecutive_count", 3)
    signal_type = fields.get("signal_type", "bullish")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
        }

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
            {"symbol": s.get("symbol", "") if isinstance(s, dict) else str(s),
             "exchange": s.get("exchange", "UNKNOWN") if isinstance(s, dict) else "UNKNOWN"}
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
                "ha_open": None, "ha_close": None, "ha_high": None, "ha_low": None,
                "consecutive_bullish": 0, "consecutive_bearish": 0, "current_price": None,
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        opens, highs, lows, closes = [], [], [], []
        for row in rows_sorted:
            try:
                opens.append(float(row.get(open_field, 0)))
                highs.append(float(row.get(high_field, 0)))
                lows.append(float(row.get(low_field, 0)))
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                opens.append(0.0); highs.append(0.0); lows.append(0.0); closes.append(0.0)

        current_price = closes[-1] if closes else None
        ha_series = calculate_heikin_ashi(opens, highs, lows, closes)

        if ha_series:
            last = ha_series[-1]
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "ha_open": last["ha_open"], "ha_close": last["ha_close"],
                "ha_high": last["ha_high"], "ha_low": last["ha_low"],
                "consecutive_bullish": last["consecutive_bullish"],
                "consecutive_bearish": last["consecutive_bearish"],
                "current_price": current_price,
            })
        else:
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "ha_open": None, "ha_close": None, "ha_high": None, "ha_low": None,
                "consecutive_bullish": 0, "consecutive_bearish": 0, "current_price": current_price,
            })

        ts = []
        for i, row in enumerate(rows_sorted):
            if i < len(ha_series):
                ts.append({
                    date_field: row.get(date_field, ""),
                    "ha_open": ha_series[i]["ha_open"],
                    "ha_close": ha_series[i]["ha_close"],
                    "ha_high": ha_series[i]["ha_high"],
                    "ha_low": ha_series[i]["ha_low"],
                    "consecutive_bullish": ha_series[i]["consecutive_bullish"],
                    "consecutive_bearish": ha_series[i]["consecutive_bearish"],
                    close_field: row.get(close_field),
                    volume_field: row.get(volume_field),
                })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": ts})

        # 조건 평가
        condition_met = False
        if ha_series and len(ha_series) >= 2:
            last = ha_series[-1]
            prev = ha_series[-2]
            if signal_type == "bullish":
                condition_met = last["consecutive_bullish"] >= consecutive_count
            elif signal_type == "bearish":
                condition_met = last["consecutive_bearish"] >= consecutive_count
            elif signal_type == "reversal_up":
                condition_met = prev["consecutive_bearish"] >= 1 and last["ha_close"] > last["ha_open"]
            elif signal_type == "reversal_down":
                condition_met = prev["consecutive_bullish"] >= 1 and last["ha_close"] < last["ha_open"]

        (passed if condition_met else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "HeikinAshi",
            "consecutive_count": consecutive_count,
            "signal_type": signal_type,
        },
    }


__all__ = ["heikin_ashi_condition", "calculate_heikin_ashi", "HEIKIN_ASHI_SCHEMA"]
