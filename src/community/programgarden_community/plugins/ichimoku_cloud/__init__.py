"""
Ichimoku Cloud (일목균형표) 플러그인

텐칸센(전환선), 기준선, 선행스팬A/B(구름대), 치코우스팬(후행스팬)을 사용한 종합 추세 분석.
- price_above_cloud: 가격이 구름대 위 (상승 추세)
- price_below_cloud: 가격이 구름대 아래 (하락 추세)
- tk_cross_bullish: 텐칸센이 기준선 상향 돌파
- tk_cross_bearish: 텐칸센이 기준선 하향 돌파
- cloud_bullish: 선행스팬A > B (구름대 양전환)
- cloud_bearish: 선행스팬A < B (구름대 음전환)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {tenkan_period, kijun_period, senkou_b_period, signal_type}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


ICHIMOKU_CLOUD_SCHEMA = PluginSchema(
    id="IchimokuCloud",
    name="Ichimoku Cloud",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Comprehensive trend analysis using Tenkan-sen, Kijun-sen, Senkou Span A/B (cloud), and Chikou Span. Supports price-cloud position, TK cross, and cloud color signals.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "tenkan_period": {
            "type": "int",
            "default": 9,
            "title": "Tenkan Period",
            "description": "Tenkan-sen (conversion line) period",
            "ge": 2,
            "le": 100,
        },
        "kijun_period": {
            "type": "int",
            "default": 26,
            "title": "Kijun Period",
            "description": "Kijun-sen (base line) period",
            "ge": 2,
            "le": 200,
        },
        "senkou_b_period": {
            "type": "int",
            "default": 52,
            "title": "Senkou Span B Period",
            "description": "Senkou Span B (leading span B) period",
            "ge": 2,
            "le": 300,
        },
        "signal_type": {
            "type": "string",
            "default": "price_above_cloud",
            "title": "Signal Type",
            "description": "Type of Ichimoku signal to detect",
            "enum": [
                "price_above_cloud",
                "price_below_cloud",
                "tk_cross_bullish",
                "tk_cross_bearish",
                "cloud_bullish",
                "cloud_bearish",
            ],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["trend", "ichimoku", "cloud", "japanese"],
    output_fields={
        "tenkan_sen": {"type": "float", "description": "Conversion line (9-period Donchian midpoint)"},
        "kijun_sen": {"type": "float", "description": "Base line (26-period Donchian midpoint)"},
        "senkou_span_a": {"type": "float", "description": "Leading span A (average of tenkan and kijun)"},
        "senkou_span_b": {"type": "float", "description": "Leading span B (52-period Donchian midpoint)"},
        "chikou_span": {"type": "float", "description": "Lagging span (current close)"},
        "current_close": {"type": "float", "description": "Current close price"},
        "cloud_top": {"type": "float", "description": "Top of the cloud (max of senkou A and B)"},
        "cloud_bottom": {"type": "float", "description": "Bottom of the cloud (min of senkou A and B)"},
    },
    locales={
        "ko": {
            "name": "일목균형표",
            "description": "텐칸센, 기준선, 선행스팬A/B(구름대), 치코우스팬을 사용한 종합 추세 분석입니다. 가격-구름 위치, TK 크로스, 구름 색상 전환 신호를 지원합니다.",
            "fields.tenkan_period": "전환선(텐칸센) 기간",
            "fields.kijun_period": "기준선(기준센) 기간",
            "fields.senkou_b_period": "선행스팬B 기간",
            "fields.signal_type": "신호 유형 (가격-구름 위치, TK 크로스, 구름 색상)",
        },
    },
)


def _donchian_mid(highs: List[float], lows: List[float], period: int) -> Optional[float]:
    """돈치안 채널 중심값 = (최고가 + 최저가) / 2"""
    if len(highs) < period or len(lows) < period:
        return None
    h = max(highs[-period:])
    l = min(lows[-period:])
    return (h + l) / 2


def calculate_ichimoku(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> Optional[Dict[str, float]]:
    """
    일목균형표 현재 값 계산

    Returns:
        {tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span} 또는 None
    """
    max_period = max(tenkan_period, kijun_period, senkou_b_period)
    if len(highs) < max_period:
        return None

    tenkan = _donchian_mid(highs, lows, tenkan_period)
    kijun = _donchian_mid(highs, lows, kijun_period)

    if tenkan is None or kijun is None:
        return None

    senkou_a = (tenkan + kijun) / 2

    senkou_b = _donchian_mid(highs, lows, senkou_b_period)
    if senkou_b is None:
        return None

    chikou = closes[-1]

    return {
        "tenkan_sen": round(tenkan, 4),
        "kijun_sen": round(kijun, 4),
        "senkou_span_a": round(senkou_a, 4),
        "senkou_span_b": round(senkou_b, 4),
        "chikou_span": round(chikou, 4),
    }


def calculate_ichimoku_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> List[Dict[str, Any]]:
    """일목균형표 시계열 계산"""
    max_period = max(tenkan_period, kijun_period, senkou_b_period)
    if len(highs) < max_period:
        return []

    results = []
    for i in range(max_period, len(highs) + 1):
        sub_h = highs[:i]
        sub_l = lows[:i]
        sub_c = closes[:i]

        vals = calculate_ichimoku(sub_h, sub_l, sub_c, tenkan_period, kijun_period, senkou_b_period)
        if vals:
            results.append(vals)

    return results


async def ichimoku_cloud_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """일목균형표 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    tenkan_period = fields.get("tenkan_period", 9)
    kijun_period = fields.get("kijun_period", 26)
    senkou_b_period = fields.get("senkou_b_period", 52)
    signal_type = fields.get("signal_type", "price_above_cloud")

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

    if symbols:
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")})
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

    max_period = max(tenkan_period, kijun_period, senkou_b_period)

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        highs, lows, closes = [], [], []
        for row in rows_sorted:
            try:
                highs.append(float(row.get(high_field, 0)))
                lows.append(float(row.get(low_field, 0)))
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(highs) < max_period:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "error": f"Insufficient data: need {max_period}, got {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 시계열 계산
        ichi_series = calculate_ichimoku_series(highs, lows, closes, tenkan_period, kijun_period, senkou_b_period)

        if not ichi_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = max_period - 1
        time_series = []

        for i, ichi_val in enumerate(ichi_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]
            current_close = closes[row_idx]

            cloud_top = max(ichi_val["senkou_span_a"], ichi_val["senkou_span_b"])
            cloud_bottom = min(ichi_val["senkou_span_a"], ichi_val["senkou_span_b"])

            signal = None
            side = "long"

            # 현재 포인트 시그널
            if signal_type == "price_above_cloud" and current_close > cloud_top:
                signal = "buy"
            elif signal_type == "price_below_cloud" and current_close < cloud_bottom:
                signal = "sell"
                side = "long"
            elif signal_type in ("tk_cross_bullish", "tk_cross_bearish") and i > 0:
                prev = ichi_series[i - 1]
                if signal_type == "tk_cross_bullish":
                    if prev["tenkan_sen"] <= prev["kijun_sen"] and ichi_val["tenkan_sen"] > ichi_val["kijun_sen"]:
                        signal = "buy"
                else:
                    if prev["tenkan_sen"] >= prev["kijun_sen"] and ichi_val["tenkan_sen"] < ichi_val["kijun_sen"]:
                        signal = "sell"
            elif signal_type == "cloud_bullish" and i > 0:
                prev = ichi_series[i - 1]
                if prev["senkou_span_a"] <= prev["senkou_span_b"] and ichi_val["senkou_span_a"] > ichi_val["senkou_span_b"]:
                    signal = "buy"
            elif signal_type == "cloud_bearish" and i > 0:
                prev = ichi_series[i - 1]
                if prev["senkou_span_a"] >= prev["senkou_span_b"] and ichi_val["senkou_span_a"] < ichi_val["senkou_span_b"]:
                    signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "tenkan_sen": ichi_val["tenkan_sen"],
                "kijun_sen": ichi_val["kijun_sen"],
                "senkou_span_a": ichi_val["senkou_span_a"],
                "senkou_span_b": ichi_val["senkou_span_b"],
                "chikou_span": ichi_val["chikou_span"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        # 마지막 값으로 조건 평가
        current = ichi_series[-1]
        current_close = closes[-1]
        cloud_top = max(current["senkou_span_a"], current["senkou_span_b"])
        cloud_bottom = min(current["senkou_span_a"], current["senkou_span_b"])

        passed_condition = False

        if signal_type == "price_above_cloud":
            passed_condition = current_close > cloud_top
        elif signal_type == "price_below_cloud":
            passed_condition = current_close < cloud_bottom
        elif signal_type == "tk_cross_bullish" and len(ichi_series) >= 2:
            prev = ichi_series[-2]
            passed_condition = prev["tenkan_sen"] <= prev["kijun_sen"] and current["tenkan_sen"] > current["kijun_sen"]
        elif signal_type == "tk_cross_bearish" and len(ichi_series) >= 2:
            prev = ichi_series[-2]
            passed_condition = prev["tenkan_sen"] >= prev["kijun_sen"] and current["tenkan_sen"] < current["kijun_sen"]
        elif signal_type == "cloud_bullish" and len(ichi_series) >= 2:
            prev = ichi_series[-2]
            passed_condition = prev["senkou_span_a"] <= prev["senkou_span_b"] and current["senkou_span_a"] > current["senkou_span_b"]
        elif signal_type == "cloud_bearish" and len(ichi_series) >= 2:
            prev = ichi_series[-2]
            passed_condition = prev["senkou_span_a"] >= prev["senkou_span_b"] and current["senkou_span_a"] < current["senkou_span_b"]

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            **current,
            "current_close": current_close,
            "cloud_top": cloud_top,
            "cloud_bottom": cloud_bottom,
        })

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
            "indicator": "IchimokuCloud",
            "tenkan_period": tenkan_period,
            "kijun_period": kijun_period,
            "senkou_b_period": senkou_b_period,
            "signal_type": signal_type,
        },
    }


__all__ = [
    "ichimoku_cloud_condition",
    "calculate_ichimoku",
    "calculate_ichimoku_series",
    "ICHIMOKU_CLOUD_SCHEMA",
]
