"""
Mean Reversion (평균 회귀) 플러그인

가격이 이동평균에서 크게 벗어났을 때 평균으로 회귀할 것을 예상하는 전략입니다.
- 가격이 MA 아래로 크게 이탈: 과매도 (매수 신호)
- 가격이 MA 위로 크게 이탈: 과매수 (매도 신호)

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {ma_period, deviation, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType
import math


MEAN_REVERSION_SCHEMA = PluginSchema(
    id="MeanReversion",
    name="Mean Reversion",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Identifies overbought/oversold conditions based on deviation from moving average. When price deviates significantly from MA, it tends to revert to the mean. Buy when oversold (price below MA by threshold), sell when overbought (price above MA by threshold).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "ma_period": {
            "type": "int",
            "default": 20,
            "title": "MA Period",
            "description": "Period for moving average calculation",
            "ge": 5,
            "le": 200,
        },
        "deviation": {
            "type": "float",
            "default": 2.0,
            "title": "Deviation Multiplier",
            "description": "Standard deviation multiplier for signal threshold",
            "ge": 1.0,
            "le": 4.0,
        },
        "direction": {
            "type": "string",
            "default": "oversold",
            "title": "Direction",
            "description": "oversold: buy when price below MA-threshold, overbought: sell when price above MA+threshold",
            "enum": ["oversold", "overbought"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["mean-reversion", "oversold", "overbought", "deviation"],
    output_fields={
        "ma": {"type": "float", "description": "Moving average value"},
        "std": {"type": "float", "description": "Standard deviation of price"},
        "upper": {"type": "float", "description": "Upper band (MA + deviation * std)"},
        "lower": {"type": "float", "description": "Lower band (MA - deviation * std)"},
        "current_price": {"type": "float", "description": "Current close price"},
        "deviation_pct": {"type": "float", "description": "Percentage deviation from MA"},
    },
    locales={
        "ko": {
            "name": "평균 회귀",
            "description": "이동평균에서 벗어난 정도를 기반으로 과매수/과매도 상태를 판단합니다. 가격이 MA에서 크게 벗어나면 평균으로 회귀하는 경향이 있습니다. 과매도(가격이 MA 아래)일 때 매수, 과매수(가격이 MA 위)일 때 매도합니다.",
            "fields.ma_period": "이동평균 계산 기간",
            "fields.deviation": "표준편차 배수 (신호 기준)",
            "fields.direction": "방향 (oversold: 과매도 매수, overbought: 과매수 매도)",
        },
    },
)


def calculate_sma(values: List[float], period: int) -> float:
    """단순 이동평균 계산"""
    if len(values) < period:
        return sum(values) / len(values) if values else 0.0
    return sum(values[-period:]) / period


def calculate_std(values: List[float], period: int) -> float:
    """표준편차 계산"""
    if len(values) < period:
        subset = values
    else:
        subset = values[-period:]

    if len(subset) < 2:
        return 0.0

    mean = sum(subset) / len(subset)
    variance = sum((x - mean) ** 2 for x in subset) / len(subset)
    return math.sqrt(variance)


def calculate_mean_reversion_series(
    closes: List[float],
    ma_period: int = 20,
    deviation: float = 2.0
) -> List[Dict[str, float]]:
    """
    평균 회귀 시계열 계산

    Returns:
        [{"ma": float, "std": float, "upper": float, "lower": float, "deviation_pct": float}, ...]
    """
    if len(closes) < ma_period:
        return []

    results = []

    for i in range(ma_period, len(closes) + 1):
        subset = closes[:i]
        ma = calculate_sma(subset, ma_period)
        std = calculate_std(subset, ma_period)

        upper = ma + std * deviation
        lower = ma - std * deviation

        current_close = subset[-1]
        deviation_pct = ((current_close - ma) / ma * 100) if ma > 0 else 0

        results.append({
            "ma": round(ma, 4),
            "std": round(std, 4),
            "upper": round(upper, 4),
            "lower": round(lower, 4),
            "deviation_pct": round(deviation_pct, 2),
        })

    return results


async def mean_reversion_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Mean Reversion 조건 평가
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

    ma_period = fields.get("ma_period", 20)
    deviation = fields.get("deviation", 2.0)
    direction = fields.get("direction", "oversold")

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
                "ma": None,
                "deviation_pct": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []

        for row in rows_sorted:
            try:
                c = float(row.get(close_field, 0))
                closes.append(c)
            except (ValueError, TypeError):
                pass

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "ma": None,
                "deviation_pct": None,
                "error": f"Insufficient data: need {min_required}, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 평균 회귀 계산
        mr_series = calculate_mean_reversion_series(closes, ma_period, deviation)

        if not mr_series:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "ma": None,
                "deviation_pct": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_mr = mr_series[-1]
        current_close = closes[-1]

        # time_series 생성
        start_idx = ma_period - 1
        time_series = []

        for i, mr_entry in enumerate(mr_series):
            row_idx = start_idx + i
            if row_idx < len(rows_sorted):
                original_row = rows_sorted[row_idx]
                close_price = closes[row_idx]

                signal = None
                side = "long"

                # 과매도/과매수 신호
                if close_price < mr_entry["lower"]:
                    signal = "buy"  # 과매도
                    side = "long"
                elif close_price > mr_entry["upper"]:
                    signal = "sell"  # 과매수
                    side = "long"

                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    open_field: original_row.get(open_field),
                    high_field: original_row.get(high_field),
                    low_field: original_row.get(low_field),
                    close_field: original_row.get(close_field),
                    volume_field: original_row.get(volume_field),
                    "ma": mr_entry["ma"],
                    "std": mr_entry["std"],
                    "upper": mr_entry["upper"],
                    "lower": mr_entry["lower"],
                    "deviation_pct": mr_entry["deviation_pct"],
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
            "ma": current_mr["ma"],
            "std": current_mr["std"],
            "upper": current_mr["upper"],
            "lower": current_mr["lower"],
            "current_price": current_close,
            "deviation_pct": current_mr["deviation_pct"],
        })

        # 조건 평가
        if direction == "oversold":
            passed_condition = current_close < current_mr["lower"]
        else:  # overbought
            passed_condition = current_close > current_mr["upper"]

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
            "indicator": "MeanReversion",
            "ma_period": ma_period,
            "deviation": deviation,
            "direction": direction,
        },
    }


__all__ = ["mean_reversion_condition", "calculate_mean_reversion_series", "MEAN_REVERSION_SCHEMA"]
