"""
RSI (Relative Strength Index) 플러그인

RSI overbought/oversold condition evaluation.
"""

from typing import List
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


RSI_SCHEMA = PluginSchema(
    id="RSI",
    name="RSI (Relative Strength Index)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="RSI overbought/oversold condition",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "Period",
            "description": "RSI calculation period",
            "ge": 2,
            "le": 100,
        },
        "threshold": {
            "type": "float",
            "default": 30,
            "title": "Threshold",
            "description": "Overbought/oversold threshold value",
            "ge": 0,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: oversold, above: overbought",
            "enum": ["below", "above"],
        },
    },
    required_data=["price_data"],
    tags=["momentum", "oscillator"],
    locales={
        "ko": {
            "name": "RSI (상대강도지수)",
            "description": "RSI 과매수/과매도 조건",
            "fields.period": "RSI 계산에 사용할 기간",
            "fields.threshold": "과매도/과매수 판단 기준값",
            "fields.direction": "방향 (below: 과매도, above: 과매수)",
        },
    },
)


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    RSI (Relative Strength Index) 계산
    
    Args:
        prices: 종가 리스트 (최신이 마지막)
        period: RSI 기간 (기본 14)
    
    Returns:
        RSI 값 (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # 데이터 부족시 중립값
    
    # 가격 변화 계산
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # 최근 period개의 변화만 사용
    recent_deltas = deltas[-(period):]
    
    # 상승/하락 분리
    gains = [d if d > 0 else 0 for d in recent_deltas]
    losses = [-d if d < 0 else 0 for d in recent_deltas]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


async def rsi_condition(symbols: list, price_data: dict, fields: dict) -> dict:
    """
    RSI 조건 평가
    
    Args:
        symbols: 평가할 종목 리스트
        price_data: 종목별 가격 데이터 {"AAPL": {"prices": [...]}}
        fields: {"period": 14, "threshold": 30, "direction": "below"}
    
    Returns:
        {"passed_symbols": [...], "failed_symbols": [...], "values": {...}}
    """
    period = fields.get("period", 14)
    threshold = fields.get("threshold", 30)
    direction = fields.get("direction", "below")
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        # 가격 데이터 추출
        symbol_data = price_data.get(symbol, {})
        prices = symbol_data.get("prices", [])
        
        # 가격 데이터가 없으면 시뮬레이션 데이터 사용
        if not prices:
            import random
            rsi_value = random.uniform(20, 80)
        else:
            rsi_value = calculate_rsi(prices, period)
        
        values[symbol] = {"rsi": rsi_value}
        
        # 조건 평가
        if direction == "below":
            passed_condition = rsi_value < threshold
        else:  # above
            passed_condition = rsi_value > threshold
        
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
            "indicator": "RSI",
            "period": period,
            "threshold": threshold,
            "direction": direction,
            "comparison": f"RSI {'<' if direction == 'below' else '>'} {threshold}",
        },
    }


__all__ = ["rsi_condition", "calculate_rsi", "RSI_SCHEMA"]
