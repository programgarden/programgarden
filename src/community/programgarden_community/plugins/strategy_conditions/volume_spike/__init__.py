"""
Volume Spike 플러그인

거래량 급증 조건을 평가합니다.
"""

from typing import List
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VOLUME_SPIKE_SCHEMA = PluginSchema(
    id="VolumeSpike",
    name="Volume Spike",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="거래량 급증 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "평균 기간",
            "ge": 5,
        },
        "multiplier": {
            "type": "float",
            "default": 2.0,
            "title": "배수",
            "description": "평균 거래량 대비 배수",
            "ge": 1.0,
        },
    },
    required_data=["volume_data"],
    tags=["volume"],
)


async def volume_spike_condition(symbols: list, volume_data: dict, fields: dict) -> dict:
    """거래량 급증 조건 평가"""
    period = fields.get("period", 20)
    multiplier = fields.get("multiplier", 2.0)
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        symbol_data = volume_data.get(symbol, {})
        volumes = symbol_data.get("volumes", [])
        current_volume = symbol_data.get("current_volume", 1000000)
        
        if volumes and len(volumes) >= period:
            avg_volume = sum(volumes[-period:]) / period
        else:
            avg_volume = 500000
        
        ratio = current_volume / avg_volume if avg_volume > 0 else 0
        values[symbol] = {
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "ratio": round(ratio, 2),
        }
        
        if current_volume > avg_volume * multiplier:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "VolumeSpike",
            "period": period,
            "multiplier": multiplier,
        },
    }


__all__ = ["volume_spike_condition", "VOLUME_SPIKE_SCHEMA"]
