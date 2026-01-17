"""
Bollinger Bands 플러그인

입력 형식 (ConditionNode와 통일):
- data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
- fields: {period, std_dev, position}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}
- symbols: [{exchange, symbol}, ...]

출력 형식:
- passed_symbols: [{exchange, symbol}, ...]
- failed_symbols: [{exchange, symbol}, ...]
- symbol_results: [{symbol, exchange, upper, middle, lower, current_price}, ...]
- values: [{symbol, exchange, time_series: [...], ...}, ...]
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


BOLLINGER_SCHEMA = PluginSchema(
    id="BollingerBands",
    name="Bollinger Bands",
    category=PluginCategory.STRATEGY_CONDITION,
    version="2.0.0",
    description="Measures how far the price has deviated from the average. Near the lower band indicates undervalued, near the upper band indicates overvalued.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "MA Period",
            "ge": 5,
            "le": 100,
        },
        "std_dev": {
            "type": "float",
            "default": 2.0,
            "title": "Std Dev Multiplier",
            "ge": 0.5,
            "le": 4.0,
        },
        "position": {
            "type": "string",
            "default": "below_lower",
            "title": "Condition Position",
            "enum": ["below_lower", "above_upper"],
        },
    },
    required_data=["data"],
    tags=["volatility", "mean-reversion"],
    locales={
        "ko": {
            "name": "볼린저밴드 (Bollinger Bands)",
            "description": "주가가 평균에서 얼마나 벗어났는지 판단합니다. 하단 밴드 근처면 저평가, 상단 밴드 근처면 고평가 상태를 나타냅니다.",
            "fields.period": "이동평균 기간",
            "fields.std_dev": "표준편차 배수",
            "fields.position": "조건 위치",
        },
    },
)


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> dict:
    """볼린저 밴드 계산"""
    if len(prices) < period:
        last_price = prices[-1] if prices else 100
        return {"upper": last_price * 1.02, "middle": last_price, "lower": last_price * 0.98}
    
    recent = prices[-period:]
    middle = sum(recent) / period
    
    variance = sum((p - middle) ** 2 for p in recent) / period
    std = variance ** 0.5
    
    return {
        "upper": round(middle + std_dev * std, 2),
        "middle": round(middle, 2),
        "lower": round(middle - std_dev * std, 2),
    }


def calculate_bollinger_series(prices: List[float], period: int = 20, std_dev: float = 2.0) -> List[dict]:
    """볼린저 밴드 시계열 계산 (time_series용)"""
    if len(prices) < period:
        return []
    
    bb_values = []
    for i in range(period, len(prices) + 1):
        sub_prices = prices[:i]
        result = calculate_bollinger_bands(sub_prices, period, std_dev)
        bb_values.append(result)
    
    return bb_values


async def bollinger_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> dict:
    """볼린저밴드 조건 평가 (새 형식: data + field_mapping)
    
    Args:
        data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
        fields: {period, std_dev, position}
        field_mapping: {필드 매핑}
        symbols: [{exchange, symbol}, ...]
    
    Returns:
        {"passed_symbols": [...], "failed_symbols": [...], "symbol_results": [...], "values": [...]}
    """
    if field_mapping is None:
        field_mapping = {}
    
    close_field = field_mapping.get("close_field", "close")
    date_field = field_mapping.get("date_field", "date")
    symbol_field = field_mapping.get("symbol_field", "symbol")
    exchange_field = field_mapping.get("exchange_field", "exchange")
    
    period = fields.get("period", 20)
    std_dev = fields.get("std_dev", 2.0)
    position = fields.get("position", "below_lower")
    
    if not data:
        return {
            "passed_symbols": [],
            "failed_symbols": symbols or [],
            "symbol_results": [],
            "values": [],
            "result": False,
        }
    
    # data를 symbol별로 그룹화
    grouped_data: Dict[str, List[Dict[str, Any]]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    
    for row in data:
        sym = row.get(symbol_field, "UNKNOWN")
        exch = row.get(exchange_field, "UNKNOWN")
        
        if sym not in grouped_data:
            grouped_data[sym] = []
            symbol_exchange_map[sym] = exch
        grouped_data[sym].append(row)
    
    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in grouped_data.keys()]
    
    passed = []
    failed = []
    symbol_results = []
    values = []
    
    for sym_info in symbols:
        if isinstance(sym_info, dict):
            symbol = sym_info.get("symbol", "")
            exchange = sym_info.get("exchange", "UNKNOWN")
        else:
            symbol = str(sym_info)
            exchange = symbol_exchange_map.get(symbol, "UNKNOWN")
        
        sym_dict = {"exchange": exchange, "symbol": symbol}
        symbol_data = grouped_data.get(symbol, [])
        symbol_data = sorted(symbol_data, key=lambda x: x.get(date_field, ""))
        
        prices = [float(row.get(close_field, 0)) for row in symbol_data if row.get(close_field)]
        current_price = prices[-1] if prices else 100
        
        if len(prices) < period:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "upper": 0,
                "middle": 0,
                "lower": 0,
                "current_price": current_price,
                "error": "insufficient_data",
            })
            continue
        
        bb_data = calculate_bollinger_bands(prices, period, std_dev)
        bb_series = calculate_bollinger_series(prices, period, std_dev)
        
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            **bb_data,
            "current_price": current_price,
        })
        
        # time_series 구성
        time_series = []
        bb_start_idx = period - 1
        for i, bb_val in enumerate(bb_series):
            bar_idx = bb_start_idx + i
            if bar_idx < len(symbol_data):
                row = symbol_data[bar_idx]
                time_series.append({
                    "date": row.get(date_field, ""),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get(close_field),
                    "volume": row.get("volume"),
                    "bb_upper": bb_val.get("upper"),
                    "bb_middle": bb_val.get("middle"),
                    "bb_lower": bb_val.get("lower"),
                })
        
        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })
        
        if position == "below_lower":
            passed_condition = current_price < bb_data["lower"]
        else:
            passed_condition = current_price > bb_data["upper"]
        
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
            "indicator": "BollingerBands",
            "period": period,
            "std_dev": std_dev,
            "position": position,
        },
    }


__all__ = ["bollinger_condition", "calculate_bollinger_bands", "calculate_bollinger_series", "BOLLINGER_SCHEMA"]
