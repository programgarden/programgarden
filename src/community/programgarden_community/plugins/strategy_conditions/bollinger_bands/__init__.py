"""
Bollinger Bands 플러그인

볼린저밴드 이탈 조건을 평가합니다.
"""

from typing import List
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


BOLLINGER_SCHEMA = PluginSchema(
    id="BollingerBands",
    name="Bollinger Bands",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="볼린저밴드 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "이동평균 기간",
            "ge": 5,
            "le": 100,
        },
        "std_dev": {
            "type": "float",
            "default": 2.0,
            "title": "표준편차 배수",
            "ge": 0.5,
            "le": 4.0,
        },
        "position": {
            "type": "string",
            "default": "below_lower",
            "title": "조건 위치",
            "enum": ["below_lower", "above_upper"],
        },
    },
    required_data=["price_data"],
    tags=["volatility", "mean-reversion"],
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


async def bollinger_condition(symbols: list, price_data: dict, fields: dict) -> dict:
    """볼린저밴드 조건 평가"""
    period = fields.get("period", 20)
    std_dev = fields.get("std_dev", 2.0)
    position = fields.get("position", "below_lower")
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        symbol_data = price_data.get(symbol, {})
        prices = symbol_data.get("prices", [])
        current_price = symbol_data.get("current_price", prices[-1] if prices else 100)
        
        if not prices:
            bb_data = {"upper": 102, "middle": 100, "lower": 98}
        else:
            bb_data = calculate_bollinger_bands(prices, period, std_dev)
        
        bb_data["current_price"] = current_price
        values[symbol] = bb_data
        
        if position == "below_lower":
            passed_condition = current_price < bb_data["lower"]
        else:
            passed_condition = current_price > bb_data["upper"]
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "BollingerBands",
            "period": period,
            "std_dev": std_dev,
            "position": position,
        },
    }


__all__ = ["bollinger_condition", "calculate_bollinger_bands", "BOLLINGER_SCHEMA"]
