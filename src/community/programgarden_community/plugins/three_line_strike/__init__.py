"""
Three Line Strike (삼선 타격) 플러그인

3연속 같은 방향 캔들 후 반대 방향의 대형 캔들(Strike)이 나타나는 패턴입니다.
- Bullish: 3연속 음봉 + 4번째 양봉이 전체를 감싸는 패턴 (매수 반전)
- Bearish: 3연속 양봉 + 4번째 음봉이 전체를 감싸는 패턴 (매도 반전)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, high, low, close, ...}, ...]
- fields: {pattern, min_body_pct}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


THREE_LINE_STRIKE_SCHEMA = PluginSchema(
    id="ThreeLineStrike",
    name="Three Line Strike",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies Three Line Strike candlestick pattern. Bullish: three consecutive bearish candles followed by a large bullish candle that engulfs all three. Bearish: three consecutive bullish candles followed by a large bearish candle. A powerful reversal signal.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "pattern": {
            "type": "string",
            "default": "bullish",
            "title": "Pattern Type",
            "description": "bullish: reversal up after 3 down candles, bearish: reversal down after 3 up candles",
            "enum": ["bullish", "bearish"],
        },
        "min_body_pct": {
            "type": "float",
            "default": 0.3,
            "title": "Minimum Body Ratio",
            "description": "Minimum candle body size as ratio of total range (high-low)",
            "ge": 0.1,
            "le": 1.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "high", "low", "close"],
    optional_fields=["volume"],
    tags=["candlestick", "pattern", "reversal", "three_line_strike"],
    locales={
        "ko": {
            "name": "삼선 타격",
            "description": "3연속 같은 방향 캔들 후 반대 방향의 대형 캔들이 나타나는 패턴을 식별합니다. Bullish: 3연속 음봉 후 대형 양봉(전체 감싸기). Bearish: 3연속 양봉 후 대형 음봉. 강력한 반전 신호입니다.",
            "fields.pattern": "패턴 유형 (bullish: 상승 반전, bearish: 하락 반전)",
            "fields.min_body_pct": "최소 몸통 비율 (전체 범위 대비)",
        },
    },
)


def is_bullish_candle(open_price: float, close_price: float) -> bool:
    """양봉 여부"""
    return close_price > open_price


def is_bearish_candle(open_price: float, close_price: float) -> bool:
    """음봉 여부"""
    return close_price < open_price


def body_ratio(open_price: float, high: float, low: float, close_price: float) -> float:
    """캔들 몸통 비율 (몸통 크기 / 전체 범위)"""
    total_range = high - low
    if total_range <= 0:
        return 0.0
    body = abs(close_price - open_price)
    return body / total_range


def detect_bullish_three_line_strike(
    candles: List[Dict[str, float]],
    min_body_pct: float = 0.3,
) -> Dict[str, Any]:
    """
    Bullish Three Line Strike 패턴 감지

    3연속 음봉 + 4번째 양봉이 3개 음봉의 시가~종가 전체를 감싸는 패턴

    Args:
        candles: 최근 4개 캔들 [{open, high, low, close}, ...]
        min_body_pct: 최소 몸통 비율

    Returns:
        {detected, confidence, details}
    """
    if len(candles) < 4:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}

    c1, c2, c3, c4 = candles[-4], candles[-3], candles[-2], candles[-1]

    # 1~3번째: 연속 음봉
    if not all(is_bearish_candle(c["open"], c["close"]) for c in [c1, c2, c3]):
        return {"detected": False, "confidence": 0, "details": "First 3 candles not all bearish"}

    # 4번째: 양봉
    if not is_bullish_candle(c4["open"], c4["close"]):
        return {"detected": False, "confidence": 0, "details": "4th candle not bullish"}

    # 각 캔들 몸통 비율 확인
    for i, c in enumerate([c1, c2, c3, c4]):
        ratio = body_ratio(c["open"], c["high"], c["low"], c["close"])
        if ratio < min_body_pct:
            return {"detected": False, "confidence": 0, "details": f"Candle {i+1} body ratio {ratio:.2f} < {min_body_pct}"}

    # 연속 하락 확인: 각 음봉의 종가가 이전보다 낮아야 함
    if not (c2["close"] < c1["close"] and c3["close"] < c2["close"]):
        return {"detected": False, "confidence": 0, "details": "Bearish candles not consecutively lower"}

    # 4번째 양봉이 3개 음봉 범위를 감싸는지 확인
    three_candle_open = c1["open"]  # 첫 음봉의 시가 (가장 높은 시작점)
    three_candle_close = c3["close"]  # 마지막 음봉의 종가 (가장 낮은 끝점)

    # Strike candle: 시가가 3번째 캔들 종가 이하, 종가가 1번째 캔들 시가 이상
    engulfing = c4["open"] <= three_candle_close and c4["close"] >= three_candle_open

    if not engulfing:
        return {"detected": False, "confidence": 0, "details": "4th candle does not engulf all 3"}

    # 신뢰도 계산
    strike_body = abs(c4["close"] - c4["open"])
    three_range = abs(three_candle_open - three_candle_close)
    confidence = min(strike_body / three_range, 2.0) / 2.0 if three_range > 0 else 0.5

    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Bullish Three Line Strike detected",
    }


def detect_bearish_three_line_strike(
    candles: List[Dict[str, float]],
    min_body_pct: float = 0.3,
) -> Dict[str, Any]:
    """
    Bearish Three Line Strike 패턴 감지

    3연속 양봉 + 4번째 음봉이 3개 양봉의 시가~종가 전체를 감싸는 패턴
    """
    if len(candles) < 4:
        return {"detected": False, "confidence": 0, "details": "Insufficient candles"}

    c1, c2, c3, c4 = candles[-4], candles[-3], candles[-2], candles[-1]

    # 1~3번째: 연속 양봉
    if not all(is_bullish_candle(c["open"], c["close"]) for c in [c1, c2, c3]):
        return {"detected": False, "confidence": 0, "details": "First 3 candles not all bullish"}

    # 4번째: 음봉
    if not is_bearish_candle(c4["open"], c4["close"]):
        return {"detected": False, "confidence": 0, "details": "4th candle not bearish"}

    # 각 캔들 몸통 비율 확인
    for i, c in enumerate([c1, c2, c3, c4]):
        ratio = body_ratio(c["open"], c["high"], c["low"], c["close"])
        if ratio < min_body_pct:
            return {"detected": False, "confidence": 0, "details": f"Candle {i+1} body ratio {ratio:.2f} < {min_body_pct}"}

    # 연속 상승 확인: 각 양봉의 종가가 이전보다 높아야 함
    if not (c2["close"] > c1["close"] and c3["close"] > c2["close"]):
        return {"detected": False, "confidence": 0, "details": "Bullish candles not consecutively higher"}

    # 4번째 음봉이 3개 양봉 범위를 감싸는지 확인
    three_candle_open = c1["open"]  # 첫 양봉의 시가 (가장 낮은 시작점)
    three_candle_close = c3["close"]  # 마지막 양봉의 종가 (가장 높은 끝점)

    # Strike candle: 시가가 3번째 캔들 종가 이상, 종가가 1번째 캔들 시가 이하
    engulfing = c4["open"] >= three_candle_close and c4["close"] <= three_candle_open

    if not engulfing:
        return {"detected": False, "confidence": 0, "details": "4th candle does not engulf all 3"}

    # 신뢰도 계산
    strike_body = abs(c4["close"] - c4["open"])
    three_range = abs(three_candle_close - three_candle_open)
    confidence = min(strike_body / three_range, 2.0) / 2.0 if three_range > 0 else 0.5

    return {
        "detected": True,
        "confidence": round(confidence, 2),
        "details": "Bearish Three Line Strike detected",
    }


async def three_line_strike_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Three Line Strike 조건 평가
    """
    mapping = field_mapping or {}
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    pattern = fields.get("pattern", "bullish")
    min_body_pct = fields.get("min_body_pct", 0.3)

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

    min_required = 4  # 최소 4일 필요

    detect_fn = detect_bullish_three_line_strike if pattern == "bullish" else detect_bearish_three_line_strike

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
                "pattern_detected": False,
                "confidence": 0,
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
                "pattern_detected": False,
                "confidence": 0,
                "error": f"Insufficient data: need {min_required}, got {len(rows_sorted)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 캔들 데이터 추출
        candles = []
        for row in rows_sorted:
            try:
                candles.append({
                    "open": float(row.get(open_field, 0)),
                    "high": float(row.get(high_field, 0)),
                    "low": float(row.get(low_field, 0)),
                    "close": float(row.get(close_field, 0)),
                })
            except (ValueError, TypeError):
                pass

        if len(candles) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "pattern_detected": False,
                "confidence": 0,
                "error": f"Insufficient valid candle data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # time_series: 4개씩 슬라이딩 윈도우로 패턴 감지
        time_series = []

        for i in range(len(rows_sorted)):
            original_row = rows_sorted[i]

            signal = None
            side = "long"
            detected = False
            confidence = 0

            if i >= 3:
                window = candles[i - 3:i + 1]
                result = detect_fn(window, min_body_pct)
                detected = result["detected"]
                confidence = result["confidence"]

                if detected:
                    if pattern == "bullish":
                        signal = "buy"
                    else:
                        signal = "sell"

            candle_type = "bullish" if is_bullish_candle(candles[i]["open"], candles[i]["close"]) else "bearish"
            b_ratio = body_ratio(candles[i]["open"], candles[i]["high"], candles[i]["low"], candles[i]["close"])

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "candle_type": candle_type,
                "body_ratio": round(b_ratio, 4),
                "pattern_detected": detected,
                "confidence": confidence,
                "signal": signal,
                "side": side,
            })

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        # 마지막 윈도우의 결과
        last_window = candles[-4:]
        last_result = detect_fn(last_window, min_body_pct)

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "pattern_detected": last_result["detected"],
            "confidence": last_result["confidence"],
            "details": last_result["details"],
            "pattern_type": pattern,
        })

        if last_result["detected"]:
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
            "indicator": "ThreeLineStrike",
            "pattern": pattern,
            "min_body_pct": min_body_pct,
        },
    }


__all__ = [
    "three_line_strike_condition",
    "detect_bullish_three_line_strike",
    "detect_bearish_three_line_strike",
    "is_bullish_candle",
    "is_bearish_candle",
    "body_ratio",
    "THREE_LINE_STRIKE_SCHEMA",
]
