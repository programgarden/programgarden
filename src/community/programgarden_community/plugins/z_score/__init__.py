"""
Z-Score 플러그인

가격의 Z-Score를 계산하여 통계적 과매도/과매수를 판단합니다.
Z = (price - mean) / std
MeanReversion과 차이: MA% 대신 표준편차 정규화로 종목 간 비교 가능.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, entry_threshold, exit_threshold, direction}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


Z_SCORE_SCHEMA = PluginSchema(
    id="ZScore",
    name="Z-Score",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Statistical Z-Score of price relative to its rolling mean and standard deviation. Z-Score normalizes deviation in standard deviation units, enabling cross-symbol comparison. Entry when |Z| exceeds entry_threshold, exit when |Z| falls below exit_threshold.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 20,
            "title": "Lookback Period",
            "description": "Rolling window for mean and std calculation",
            "ge": 5,
            "le": 252,
        },
        "entry_threshold": {
            "type": "float",
            "default": 2.0,
            "title": "Entry Threshold (sigma)",
            "description": "Z-Score threshold for entry signal",
            "ge": 0.5,
            "le": 5.0,
        },
        "exit_threshold": {
            "type": "float",
            "default": 0.5,
            "title": "Exit Threshold (sigma)",
            "description": "Z-Score threshold for exit signal (mean reversion completion)",
            "ge": 0.0,
            "le": 3.0,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: buy when Z < -entry (oversold), above: sell when Z > +entry (overbought)",
            "enum": ["below", "above"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["zscore", "statistics", "mean-reversion", "normalized"],
    locales={
        "ko": {
            "name": "Z-Score (표준점수)",
            "description": "가격의 Z-Score를 계산하여 통계적 과매도/과매수를 판단합니다. Z-Score는 표준편차 단위로 정규화되어 종목 간 비교가 가능합니다. |Z|가 진입 임계값을 넘으면 진입, 청산 임계값 아래로 내려가면 청산합니다.",
            "fields.lookback": "롤링 윈도우 기간",
            "fields.entry_threshold": "진입 임계값 (시그마)",
            "fields.exit_threshold": "청산 임계값 (시그마)",
            "fields.direction": "방향 (below: Z < -entry 시 매수, above: Z > +entry 시 매도)",
        },
    },
)


def calculate_z_score(prices: List[float], lookback: int = 20) -> Optional[float]:
    """
    최신 가격의 Z-Score 계산

    Args:
        prices: 종가 리스트 (오래된→최신)
        lookback: 롤링 윈도우

    Returns:
        Z-Score 값 또는 None (데이터 부족)
    """
    if len(prices) < lookback:
        return None

    window = prices[-lookback:]
    mean = sum(window) / lookback
    variance = sum((x - mean) ** 2 for x in window) / lookback
    std = math.sqrt(variance)

    if std == 0:
        return 0.0

    return round((prices[-1] - mean) / std, 4)


def calculate_z_score_series(prices: List[float], lookback: int = 20) -> List[Dict[str, float]]:
    """
    Z-Score 시계열 계산

    Returns:
        [{"z_score": float, "mean": float, "std": float}, ...]
    """
    if len(prices) < lookback:
        return []

    results = []
    for i in range(lookback, len(prices) + 1):
        window = prices[i - lookback:i]
        mean = sum(window) / lookback
        variance = sum((x - mean) ** 2 for x in window) / lookback
        std = math.sqrt(variance)

        z = (prices[i - 1] - mean) / std if std > 0 else 0.0

        results.append({
            "z_score": round(z, 4),
            "mean": round(mean, 4),
            "std": round(std, 4),
        })

    return results


async def z_score_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Z-Score 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {lookback, entry_threshold, exit_threshold, direction}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과 (passed_symbols, failed_symbols, symbol_results, values, result)
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    lookback = fields.get("lookback", 20)
    entry_threshold = fields.get("entry_threshold", 2.0)
    exit_threshold = fields.get("exit_threshold", 0.5)
    direction = fields.get("direction", "below")

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
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < lookback:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "z_score": None, "current_price": None,
                "error": f"Insufficient data: need {lookback}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(closes) < lookback:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "z_score": None, "current_price": None,
                "error": f"Insufficient price data: need {lookback}, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # Z-Score 시계열 계산
        z_series = calculate_z_score_series(closes, lookback)
        current_z = z_series[-1]["z_score"] if z_series else None
        current_price = closes[-1]

        # time_series 생성
        start_idx = lookback - 1
        time_series = []
        for i, z_entry in enumerate(z_series):
            row_idx = start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]
                z_val = z_entry["z_score"]

                signal = None
                side = "long"
                if direction == "below":
                    if z_val < -entry_threshold:
                        signal = "buy"
                    elif z_val > -exit_threshold and z_val < 0:
                        signal = "exit"
                else:  # above
                    if z_val > entry_threshold:
                        signal = "sell"
                    elif z_val < exit_threshold and z_val > 0:
                        signal = "exit"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "z_score": z_val,
                    "mean": z_entry["mean"],
                    "std": z_entry["std"],
                    "signal": signal,
                    "side": side,
                })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "z_score": current_z,
            "mean": z_series[-1]["mean"] if z_series else None,
            "std": z_series[-1]["std"] if z_series else None,
            "current_price": current_price,
        })

        # 조건 평가
        if current_z is not None:
            if direction == "below":
                passed_condition = current_z < -entry_threshold
            else:
                passed_condition = current_z > entry_threshold

            (passed if passed_condition else failed).append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ZScore",
            "lookback": lookback,
            "entry_threshold": entry_threshold,
            "exit_threshold": exit_threshold,
            "direction": direction,
            "comparison": f"Z {'< -' if direction == 'below' else '> +'}{entry_threshold}",
        },
    }


__all__ = ["z_score_condition", "calculate_z_score", "calculate_z_score_series", "Z_SCORE_SCHEMA"]
