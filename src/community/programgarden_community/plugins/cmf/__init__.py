"""
CMF (Chaikin Money Flow, 차이킨 자금흐름) 플러그인

매집(accumulation)과 분산(distribution)을 거래량으로 측정. 양수=매집, 음수=분산.
- accumulation: CMF > threshold (매집)
- distribution: CMF < -threshold (분산)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, volume, ...}, ...]
- fields: {period, threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CMF_SCHEMA = PluginSchema(
    id="CMF",
    name="Chaikin Money Flow",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures accumulation and distribution using volume-weighted price. Positive CMF indicates accumulation (buying), negative indicates distribution (selling). Complements OBV.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "Period",
            "description": "CMF calculation period",
            "ge": 2,
            "le": 100,
        },
        "threshold": {
            "type": "float",
            "default": 0.05,
            "title": "Threshold",
            "description": "Accumulation/distribution threshold",
            "ge": 0.01,
            "le": 0.5,
        },
        "direction": {
            "type": "string",
            "default": "accumulation",
            "title": "Direction",
            "description": "accumulation: CMF > threshold, distribution: CMF < -threshold",
            "enum": ["accumulation", "distribution"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low", "volume"],
    optional_fields=["open"],
    tags=["volume", "accumulation", "distribution", "chaikin"],
    locales={
        "ko": {
            "name": "차이킨 자금흐름 (CMF)",
            "description": "거래량 가중 가격으로 매집과 분산을 측정합니다. 양의 CMF는 매집(매수세), 음의 CMF는 분산(매도세)을 나타냅니다.",
            "fields.period": "CMF 계산 기간",
            "fields.threshold": "매집/분산 기준값",
            "fields.direction": "방향 (accumulation: 매집, distribution: 분산)",
        },
    },
)


def calculate_cmf(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 20,
) -> Optional[float]:
    """
    CMF = sum(MFV, period) / sum(Volume, period)
    MFV = MFM * Volume
    MFM = ((Close - Low) - (High - Close)) / (High - Low)
    """
    if len(highs) < period:
        return None

    mfv_sum = 0.0
    vol_sum = 0.0

    for i in range(len(highs) - period, len(highs)):
        hl_range = highs[i] - lows[i]
        if hl_range == 0:
            mfm = 0.0
        else:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl_range
        mfv_sum += mfm * volumes[i]
        vol_sum += volumes[i]

    if vol_sum == 0:
        return 0.0

    return round(mfv_sum / vol_sum, 4)


def calculate_cmf_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 20,
) -> List[Dict[str, Any]]:
    """CMF 시계열"""
    if len(highs) < period:
        return []

    results = []
    for i in range(period, len(highs) + 1):
        cmf = calculate_cmf(highs[:i], lows[:i], closes[:i], volumes[:i], period)
        # 마지막 MFV
        hl_range = highs[i - 1] - lows[i - 1]
        mfm = ((closes[i - 1] - lows[i - 1]) - (highs[i - 1] - closes[i - 1])) / hl_range if hl_range > 0 else 0
        mfv = round(mfm * volumes[i - 1], 4)
        results.append({"cmf": cmf, "mfv": mfv})

    return results


async def cmf_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """CMF 조건 평가"""
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    volume_field = mapping.get("volume_field", "volume")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")

    period = fields.get("period", 20)
    threshold = fields.get("threshold", 0.05)
    direction = fields.get("direction", "accumulation")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [], "symbol_results": [],
            "values": [], "result": False, "analysis": {"error": "No data provided"},
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
            {"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")} if isinstance(s, dict)
            else {"symbol": str(s), "exchange": "UNKNOWN"} for s in symbols
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

        if not rows or len(rows) < period:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "cmf": None, "error": "Insufficient data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        highs, lows, closes, vols = [], [], [], []
        for row in rows_sorted:
            try:
                highs.append(float(row.get(high_field, 0)))
                lows.append(float(row.get(low_field, 0)))
                closes.append(float(row.get(close_field, 0)))
                vols.append(float(row.get(volume_field, 0)))
            except (ValueError, TypeError):
                pass

        cmf_series = calculate_cmf_series(highs, lows, closes, vols, period)
        if not cmf_series:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "cmf": None, "error": "Calculation failed"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        start_idx = period - 1
        time_series = []

        for i, cmf_val in enumerate(cmf_series):
            row_idx = start_idx + i
            if row_idx >= len(rows_sorted):
                break
            original_row = rows_sorted[row_idx]

            signal = None
            side = "long"
            if cmf_val["cmf"] is not None:
                if cmf_val["cmf"] > threshold:
                    signal = "buy"
                elif cmf_val["cmf"] < -threshold:
                    signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "cmf": cmf_val["cmf"],
                "mfv": cmf_val["mfv"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        current_cmf = cmf_series[-1]["cmf"]
        symbol_results.append({
            "symbol": symbol, "exchange": exchange, "cmf": current_cmf, "mfv": cmf_series[-1]["mfv"],
        })

        if direction == "accumulation":
            passed_condition = current_cmf is not None and current_cmf > threshold
        else:
            passed_condition = current_cmf is not None and current_cmf < -threshold

        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "CMF", "period": period, "threshold": threshold, "direction": direction},
    }


__all__ = ["cmf_condition", "calculate_cmf", "calculate_cmf_series", "CMF_SCHEMA"]
