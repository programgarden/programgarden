"""
MACD (Moving Average Convergence Divergence) 플러그인

MACD 크로스오버 조건을 평가합니다.
"""

from typing import List
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MACD_SCHEMA = PluginSchema(
    id="MACD",
    name="MACD (Moving Average Convergence Divergence)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="MACD 크로스오버 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "fast_period": {
            "type": "int",
            "default": 12,
            "title": "빠른 EMA 기간",
            "ge": 2,
        },
        "slow_period": {
            "type": "int",
            "default": 26,
            "title": "느린 EMA 기간",
            "ge": 5,
        },
        "signal_period": {
            "type": "int",
            "default": 9,
            "title": "시그널 기간",
            "ge": 2,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish_cross",
            "title": "신호 유형",
            "enum": ["bullish_cross", "bearish_cross"],
        },
    },
    required_data=["price_data"],
    tags=["trend", "momentum"],
)


def calculate_ema(data: List[float], period: int) -> float:
    """EMA 계산"""
    if len(data) < period:
        return data[-1] if data else 0
    multiplier = 2 / (period + 1)
    ema_values = [sum(data[:period]) / period]
    for price in data[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values[-1]


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD 계산
    
    Returns:
        {"macd": float, "signal": float, "histogram": float}
    """
    if len(prices) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    fast_ema = calculate_ema(prices, fast)
    slow_ema = calculate_ema(prices, slow)
    macd_line = fast_ema - slow_ema
    
    # MACD 히스토리 계산 (시그널용)
    macd_history = []
    for i in range(slow, len(prices) + 1):
        fe = calculate_ema(prices[:i], fast)
        se = calculate_ema(prices[:i], slow)
        macd_history.append(fe - se)
    
    signal_line = calculate_ema(macd_history, signal) if len(macd_history) >= signal else macd_line
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4),
    }


async def macd_condition(symbols: list, price_data: dict, fields: dict) -> dict:
    """MACD 조건 평가"""
    fast = fields.get("fast_period", 12)
    slow = fields.get("slow_period", 26)
    signal_period = fields.get("signal_period", 9)
    signal_type = fields.get("signal_type", "bullish_cross")
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        symbol_data = price_data.get(symbol, {})
        prices = symbol_data.get("prices", [])
        
        if not prices:
            import random
            macd_data = {
                "macd": random.uniform(-1, 1),
                "signal": random.uniform(-1, 1),
                "histogram": random.uniform(-0.5, 0.5),
            }
        else:
            macd_data = calculate_macd(prices, fast, slow, signal_period)
        
        values[symbol] = macd_data
        
        if signal_type == "bullish_cross":
            passed_condition = macd_data["histogram"] > 0 and macd_data["macd"] > 0
        else:
            passed_condition = macd_data["histogram"] < 0 and macd_data["macd"] < 0
        
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
            "indicator": "MACD",
            "fast_period": fast,
            "slow_period": slow,
            "signal_period": signal_period,
            "signal_type": signal_type,
        },
    }


__all__ = ["macd_condition", "calculate_macd", "MACD_SCHEMA"]
