"""
VWAP (거래량가중평균가격) 플러그인

거래량 가중 평균가격. 가격이 VWAP 위면 매수 우위, 아래면 매도 우위.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, volume, ...}, ...]
- fields: {direction, band_multiplier}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VWAP_SCHEMA = PluginSchema(
    id="VWAP",
    name="VWAP",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Volume Weighted Average Price. Price above VWAP indicates buying pressure, below indicates selling pressure. Optional standard deviation bands.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "direction": {
            "type": "string",
            "default": "above",
            "title": "Direction",
            "description": "Price position relative to VWAP (above/below)",
            "enum": ["above", "below"],
        },
        "band_multiplier": {
            "type": "float",
            "default": 0.0,
            "title": "Band Multiplier",
            "description": "Standard deviation band multiplier (0 = no bands)",
            "ge": 0.0,
            "le": 5.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "volume"],
    optional_fields=["high", "low", "open"],
    tags=["volume", "vwap", "intraday"],
    output_fields={
        "vwap": {"type": "float", "description": "Volume weighted average price"},
        "current_close": {"type": "float", "description": "Current close price"},
        "upper_band": {"type": "float", "description": "Upper standard deviation band (None if band_multiplier=0)"},
        "lower_band": {"type": "float", "description": "Lower standard deviation band (None if band_multiplier=0)"},
    },
    locales={
        "ko": {
            "name": "거래량가중평균가격 (VWAP)",
            "description": "거래량 가중 평균가격입니다. 가격이 VWAP 위면 매수 우위, 아래면 매도 우위를 나타냅니다. 표준편차 밴드 옵션을 지원합니다.",
            "fields.direction": "가격 위치 (above: VWAP 위, below: VWAP 아래)",
            "fields.band_multiplier": "표준편차 밴드 배수 (0 = 밴드 없음)",
        },
    },
)


def calculate_vwap(
    closes: List[float],
    volumes: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
) -> Optional[float]:
    """
    VWAP 계산: sum(TP * Volume) / sum(Volume)
    TP = (High + Low + Close) / 3, high/low 없으면 close 사용
    """
    if not closes or not volumes or len(closes) != len(volumes):
        return None

    total_tpv = 0.0
    total_vol = 0.0

    for i in range(len(closes)):
        if highs and lows and i < len(highs) and i < len(lows):
            tp = (highs[i] + lows[i] + closes[i]) / 3
        else:
            tp = closes[i]
        vol = volumes[i]
        total_tpv += tp * vol
        total_vol += vol

    if total_vol == 0:
        return None

    return round(total_tpv / total_vol, 4)


def calculate_vwap_series(
    closes: List[float],
    volumes: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    band_multiplier: float = 0.0,
) -> List[Dict[str, Any]]:
    """VWAP 시계열 + 밴드 계산"""
    if not closes or not volumes:
        return []

    results = []
    cum_tpv = 0.0
    cum_vol = 0.0
    tp_values = []

    for i in range(len(closes)):
        if highs and lows and i < len(highs) and i < len(lows):
            tp = (highs[i] + lows[i] + closes[i]) / 3
        else:
            tp = closes[i]

        vol = volumes[i]
        cum_tpv += tp * vol
        cum_vol += vol
        tp_values.append(tp)

        if cum_vol == 0:
            results.append({"vwap": 0, "upper_band": None, "lower_band": None})
            continue

        vwap = cum_tpv / cum_vol

        upper_band = None
        lower_band = None
        if band_multiplier > 0 and len(tp_values) > 1:
            # 누적 표준편차
            mean = sum(tp_values) / len(tp_values)
            variance = sum((x - mean) ** 2 for x in tp_values) / len(tp_values)
            std = variance ** 0.5
            upper_band = round(vwap + band_multiplier * std, 4)
            lower_band = round(vwap - band_multiplier * std, 4)

        results.append({
            "vwap": round(vwap, 4),
            "upper_band": upper_band,
            "lower_band": lower_band,
        })

    return results


async def vwap_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """VWAP 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    volume_field = mapping.get("volume_field", "volume")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")

    direction = fields.get("direction", "above")
    band_multiplier = fields.get("band_multiplier", 0.0)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
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

        closes, vols, highs, lows = [], [], [], []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
                vols.append(float(row.get(volume_field, 0)))
                h = row.get(high_field)
                l = row.get(low_field)
                highs.append(float(h) if h is not None else None)
                lows.append(float(l) if l is not None else None)
            except (ValueError, TypeError):
                pass

        if not closes:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No valid data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        has_hl = all(x is not None for x in highs) and all(x is not None for x in lows)
        h_list = highs if has_hl else None
        l_list = lows if has_hl else None

        vwap_series = calculate_vwap_series(closes, vols, h_list, l_list, band_multiplier)

        time_series = []
        for i, vwap_val in enumerate(vwap_series):
            if i >= len(rows_sorted):
                break
            original_row = rows_sorted[i]
            current_close = closes[i]

            signal = None
            side = "long"
            if vwap_val["vwap"] > 0:
                if current_close > vwap_val["vwap"]:
                    signal = "buy"
                elif current_close < vwap_val["vwap"]:
                    signal = "sell"

            time_series.append({
                date_field: original_row.get(date_field, ""),
                open_field: original_row.get(open_field),
                high_field: original_row.get(high_field),
                low_field: original_row.get(low_field),
                close_field: original_row.get(close_field),
                volume_field: original_row.get(volume_field),
                "vwap": vwap_val["vwap"],
                "upper_band": vwap_val["upper_band"],
                "lower_band": vwap_val["lower_band"],
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        # 최종 VWAP 값
        last_vwap = vwap_series[-1]["vwap"] if vwap_series else 0
        current_close = closes[-1]

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "vwap": last_vwap,
            "current_close": current_close,
            "upper_band": vwap_series[-1]["upper_band"] if vwap_series else None,
            "lower_band": vwap_series[-1]["lower_band"] if vwap_series else None,
        })

        if direction == "above":
            passed_condition = current_close > last_vwap and last_vwap > 0
        else:
            passed_condition = current_close < last_vwap and last_vwap > 0

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
            "indicator": "VWAP",
            "direction": direction,
            "band_multiplier": band_multiplier,
        },
    }


__all__ = ["vwap_condition", "calculate_vwap", "calculate_vwap_series", "VWAP_SCHEMA"]
