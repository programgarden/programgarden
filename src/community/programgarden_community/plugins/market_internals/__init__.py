"""
MarketInternals (시장 내부 지표) 플러그인

유니버스 전체 건강도를 측정합니다:
- advance_decline_ratio: 상승/하락 비율
- above_ma_pct: MA 위 종목 비율
- new_high_low_ratio: 신고/신저가 비율
- composite: 복합 점수

입력 형식:
- data: 플랫 배열 (다종목 데이터 포함)
- fields: {lookback, ma_period, high_low_period, metric, threshold, direction}

※ 다중 종목 플러그인 - ConditionNode auto-iterate 제약 → NodeRunner 테스트 권장
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MARKET_INTERNALS_SCHEMA = PluginSchema(
    id="MarketInternals",
    name="Market Internals",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Measures universe health: advance/decline ratio, % above moving average, new high/low ratio, or composite score. Provides a market breadth indicator to gauge overall market conditions.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 1,
            "title": "Lookback Period",
            "description": "Period for advance/decline comparison",
            "ge": 1,
            "le": 30,
        },
        "ma_period": {
            "type": "int",
            "default": 50,
            "title": "MA Period",
            "description": "Moving average period for above_ma_pct metric",
            "ge": 5,
            "le": 200,
        },
        "high_low_period": {
            "type": "int",
            "default": 52,
            "title": "High/Low Period",
            "description": "Period for new high/low detection (in data points)",
            "ge": 10,
            "le": 252,
        },
        "metric": {
            "type": "string",
            "default": "advance_decline_ratio",
            "title": "Metric",
            "description": "Market breadth metric to evaluate",
            "enum": ["advance_decline_ratio", "above_ma_pct", "new_high_low_ratio", "composite"],
        },
        "threshold": {
            "type": "float",
            "default": 60.0,
            "title": "Threshold (%)",
            "description": "Threshold percentage for condition evaluation",
            "ge": 0.0,
            "le": 100.0,
        },
        "direction": {
            "type": "string",
            "default": "above",
            "title": "Direction",
            "description": "above: healthy market (value > threshold), below: weak market (value < threshold)",
            "enum": ["above", "below"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["high", "low"],
    tags=["breadth", "market", "internals", "advance_decline", "health"],
    output_fields={
        "change_pct": {"type": "float", "description": "Price change percentage for this symbol over the lookback period"},
        "above_ma": {"type": "bool", "description": "Whether this symbol's price is above its own moving average"},
        "current_price": {"type": "float", "description": "Latest closing price of this symbol"},
    },
    locales={
        "ko": {
            "name": "시장 내부 지표 (Market Internals)",
            "description": "유니버스 전체의 건강도를 측정합니다. 상승/하락 비율, MA 위 종목 비율, 신고/신저가 비율 또는 복합 점수를 통해 시장 폭을 평가합니다.",
            "fields.lookback": "상승/하락 비교 기간",
            "fields.ma_period": "이동평균 기간 (above_ma_pct 용)",
            "fields.high_low_period": "신고/신저가 기간 (데이터 포인트)",
            "fields.metric": "지표 (advance_decline_ratio/above_ma_pct/new_high_low_ratio/composite)",
            "fields.threshold": "임계값 (%)",
            "fields.direction": "방향 (above: 건강한 시장, below: 약한 시장)",
        },
    },
)


def _calculate_advance_decline(symbol_closes: Dict[str, List[float]], lookback: int) -> float:
    """상승/하락 비율 (%) - 상승 종목 비율"""
    advancing = 0
    total = 0

    for sym, closes in symbol_closes.items():
        if len(closes) <= lookback:
            continue
        total += 1
        if closes[-1] > closes[-1 - lookback]:
            advancing += 1

    return (advancing / total * 100) if total > 0 else 50.0


def _calculate_above_ma_pct(symbol_closes: Dict[str, List[float]], ma_period: int) -> float:
    """MA 위 종목 비율 (%)"""
    above = 0
    total = 0

    for sym, closes in symbol_closes.items():
        if len(closes) < ma_period:
            continue
        total += 1
        ma = sum(closes[-ma_period:]) / ma_period
        if closes[-1] > ma:
            above += 1

    return (above / total * 100) if total > 0 else 50.0


def _calculate_new_high_low_ratio(symbol_closes: Dict[str, List[float]], period: int) -> float:
    """신고가 종목 비율 (%)"""
    new_high = 0
    total = 0

    for sym, closes in symbol_closes.items():
        if len(closes) < period:
            continue
        total += 1
        window = closes[-period:]
        if closes[-1] >= max(window):
            new_high += 1

    return (new_high / total * 100) if total > 0 else 50.0


async def market_internals_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """시장 내부 지표 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 1)
    ma_period = fields.get("ma_period", 50)
    high_low_period = fields.get("high_low_period", 52)
    metric = fields.get("metric", "advance_decline_ratio")
    threshold = fields.get("threshold", 60.0)
    direction = fields.get("direction", "above")

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

    # 종목별 종가 시계열 추출
    symbol_closes: Dict[str, List[float]] = {}
    for sym, rows in symbol_data_map.items():
        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass
        if closes:
            symbol_closes[sym] = closes

    if len(symbol_closes) < 2:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "Need at least 2 symbols for market internals"},
        }

    # 지표 계산
    ad_ratio = _calculate_advance_decline(symbol_closes, lookback)
    above_ma = _calculate_above_ma_pct(symbol_closes, ma_period)
    nh_ratio = _calculate_new_high_low_ratio(symbol_closes, high_low_period)

    if metric == "advance_decline_ratio":
        metric_value = ad_ratio
    elif metric == "above_ma_pct":
        metric_value = above_ma
    elif metric == "new_high_low_ratio":
        metric_value = nh_ratio
    else:  # composite
        metric_value = (ad_ratio + above_ma + nh_ratio) / 3

    metric_value = round(metric_value, 2)

    # 조건 평가
    if direction == "above":
        condition_met = metric_value > threshold
    else:
        condition_met = metric_value < threshold

    # 개별 종목 결과
    passed, failed, symbol_results, values = [], [], [], []
    target_symbols = symbols or [
        {"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")}
        for s in symbol_closes.keys()
    ]

    for sym_info in target_symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        closes = symbol_closes.get(symbol, [])
        change = 0.0
        if closes and len(closes) > lookback:
            prev = closes[-1 - lookback]
            change = ((closes[-1] - prev) / prev * 100) if prev > 0 else 0.0

        above_own_ma = False
        if closes and len(closes) >= ma_period:
            ma = sum(closes[-ma_period:]) / ma_period
            above_own_ma = closes[-1] > ma

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "change_pct": round(change, 2),
            "above_ma": above_own_ma,
            "current_price": closes[-1] if closes else None,
        })
        values.append({"symbol": symbol, "exchange": exchange, "time_series": []})

        if condition_met:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    market_health = {
        "advance_decline_ratio": round(ad_ratio, 2),
        "above_ma_pct": round(above_ma, 2),
        "new_high_low_ratio": round(nh_ratio, 2),
        "composite": round((ad_ratio + above_ma + nh_ratio) / 3, 2),
        "metric_used": metric,
        "metric_value": metric_value,
        "condition_met": condition_met,
    }

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "market_health": market_health,
        "result": condition_met,
        "analysis": {
            "indicator": "MarketInternals",
            "metric": metric,
            "metric_value": metric_value,
            "threshold": threshold,
            "direction": direction,
            "total_symbols": len(symbol_closes),
        },
    }


__all__ = ["market_internals_condition", "MARKET_INTERNALS_SCHEMA"]
