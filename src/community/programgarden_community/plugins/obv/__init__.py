"""
OBV (On-Balance Volume) 플러그인

거래량을 기반으로 추세를 확인합니다.
- 가격 상승 시: 거래량 추가
- 가격 하락 시: 거래량 차감
- OBV > OBV MA: 상승 추세 (매수세 우위)
- OBV < OBV MA: 하락 추세 (매도세 우위)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, volume, ...}, ...]
- fields: {ma_period, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


OBV_SCHEMA = PluginSchema(
    id="OBV",
    name="OBV (On-Balance Volume)",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Tracks cumulative buying/selling pressure using volume flow. OBV above its MA indicates bullish momentum, below indicates bearish momentum. Divergence between OBV and price can signal trend reversals.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "ma_period": {
            "type": "int",
            "default": 20,
            "title": "MA Period",
            "description": "Period for OBV moving average",
            "ge": 5,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "bullish",
            "title": "Direction",
            "description": "bullish: OBV above MA, bearish: OBV below MA",
            "enum": ["bullish", "bearish"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "volume"],
    optional_fields=["open", "high", "low"],
    tags=["volume", "trend", "momentum"],
    locales={
        "ko": {
            "name": "OBV (거래량 균형)",
            "description": "거래량 흐름을 통해 매수/매도 압력을 추적합니다. OBV가 이동평균 위에 있으면 상승 모멘텀, 아래에 있으면 하락 모멘텀을 나타냅니다. OBV와 가격의 다이버전스는 추세 전환 신호가 될 수 있습니다.",
            "fields.ma_period": "OBV 이동평균 기간",
            "fields.direction": "방향 (bullish: OBV가 MA 위, bearish: OBV가 MA 아래)",
        },
    },
)


def calculate_obv(closes: List[float], volumes: List[float]) -> float:
    """
    OBV 계산

    Args:
        closes: 종가 배열
        volumes: 거래량 배열

    Returns:
        현재 OBV 값
    """
    if len(closes) < 2 or len(volumes) < 2:
        return 0.0

    obv = 0.0

    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        # closes[i] == closes[i-1] 이면 변화 없음

    return obv


def calculate_obv_series(
    closes: List[float],
    volumes: List[float],
    ma_period: int = 20
) -> List[Dict[str, float]]:
    """
    OBV 시계열 계산

    Returns:
        [{"obv": float, "obv_ma": float}, ...]
    """
    if len(closes) < 2 or len(volumes) < 2:
        return []

    obv_values = [0.0]  # 첫 번째 OBV는 0

    for i in range(1, len(closes)):
        prev_obv = obv_values[-1]
        if closes[i] > closes[i-1]:
            obv_values.append(prev_obv + volumes[i])
        elif closes[i] < closes[i-1]:
            obv_values.append(prev_obv - volumes[i])
        else:
            obv_values.append(prev_obv)

    # OBV MA 계산
    results = []
    for i in range(len(obv_values)):
        obv = obv_values[i]

        # MA 계산 (충분한 데이터가 있을 때만)
        if i >= ma_period - 1:
            obv_ma = sum(obv_values[i - ma_period + 1:i + 1]) / ma_period
        else:
            obv_ma = sum(obv_values[:i + 1]) / (i + 1)

        results.append({
            "obv": round(obv, 2),
            "obv_ma": round(obv_ma, 2),
        })

    return results


async def obv_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    OBV 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {ma_period, direction}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        {passed_symbols, failed_symbols, symbol_results, values, result}
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    volume_field = mapping.get("volume_field", "volume")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")

    ma_period = fields.get("ma_period", 20)
    direction = fields.get("direction", "bullish")

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

    min_required = ma_period

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
                "obv": None,
                "obv_ma": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []
        volumes = []

        for row in rows_sorted:
            try:
                c = float(row.get(close_field, 0))
                v = float(row.get(volume_field, 0))
                closes.append(c)
                volumes.append(v)
            except (ValueError, TypeError):
                pass

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "obv": None,
                "obv_ma": None,
                "error": f"Insufficient data: need {min_required}, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # OBV 계산
        obv_series = calculate_obv_series(closes, volumes, ma_period)

        if not obv_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "obv": None,
                "obv_ma": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_obv = obv_series[-1]
        obv_val = current_obv["obv"]
        obv_ma = current_obv["obv_ma"]

        # time_series 생성
        time_series = []

        for i, obv_entry in enumerate(obv_series):
            if i < len(rows_sorted):
                original_row = rows_sorted[i]

                signal = None
                side = "long"

                # 신호 생성
                is_bullish = obv_entry["obv"] > obv_entry["obv_ma"]

                if is_bullish:
                    signal = "buy"
                    side = "long"
                else:
                    signal = "sell"
                    side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "obv": obv_entry["obv"],
                    "obv_ma": obv_entry["obv_ma"],
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
            "obv": obv_val,
            "obv_ma": obv_ma,
        })

        # 조건 평가
        is_bullish = obv_val > obv_ma

        if direction == "bullish":
            passed_condition = is_bullish
        else:  # bearish
            passed_condition = not is_bullish

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
            "indicator": "OBV",
            "ma_period": ma_period,
            "direction": direction,
        },
    }


__all__ = ["obv_condition", "calculate_obv", "calculate_obv_series", "OBV_SCHEMA"]
