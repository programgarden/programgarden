"""
MovingAverageCross (이동평균선 크로스) 플러그인

입력 형식 (ConditionNode와 통일):
- data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
- fields: {short_period, long_period, cross_type}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}
- symbols: [{exchange, symbol}, ...]
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MA_CROSS_SCHEMA = PluginSchema(
    id="MovingAverageCross",
    name="Moving Average Cross",
    category=PluginCategory.TECHNICAL,
    version="3.0.0",
    description="Golden Cross (bullish) when short MA crosses above long MA, Dead Cross (bearish) when crossing below.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "short_period": {"type": "int", "default": 5, "title": "Short MA Period"},
        "long_period": {"type": "int", "default": 20, "title": "Long MA Period"},
        "cross_type": {"type": "string", "default": "golden", "enum": ["golden", "dead"], "title": "Cross Type"},
    },
    required_data=["data"],
    # items { from, extract } 필수 필드 (v3.0.0+)
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["trend", "moving_average", "crossover"],
    output_fields={
        "short_ma": {"type": "float", "description": "Current short-period moving average value"},
        "long_ma": {"type": "float", "description": "Current long-period moving average value"},
        "status": {"type": "str", "description": "Trend status: 'bullish' or 'bearish'"},
    },
    locales={
        "ko": {
            "name": "이동평균선 크로스 (MA Cross)",
            "description": "단기 이동평균이 장기 이동평균을 위로 돌파하면 골든크로스(상승 신호), 아래로 돌파하면 데드크로스(하락 신호)로 해석합니다.",
            "fields.short_period": "단기 MA 기간",
            "fields.long_period": "장기 MA 기간",
            "fields.cross_type": "크로스 유형",
        },
    },
)


def calculate_sma(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0
    return sum(prices[-period:]) / period


def calculate_sma_series(prices: List[float], period: int) -> List[float]:
    if len(prices) < period:
        return []
    return [sum(prices[i - period + 1:i + 1]) / period for i in range(period - 1, len(prices))]


def detect_crossover(short_ma: List[float], long_ma: List[float], cross_type: str = "golden") -> List[int]:
    min_len = min(len(short_ma), len(long_ma))
    short_ma, long_ma = short_ma[-min_len:], long_ma[-min_len:]
    crossover_indices = []
    for i in range(1, min_len):
        if cross_type == "golden":
            if short_ma[i - 1] <= long_ma[i - 1] and short_ma[i] > long_ma[i]:
                crossover_indices.append(i)
        else:
            if short_ma[i - 1] >= long_ma[i - 1] and short_ma[i] < long_ma[i]:
                crossover_indices.append(i)
    return crossover_indices


async def ma_cross_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> dict:
    if field_mapping is None:
        field_mapping = {}
    
    close_field = field_mapping.get("close_field", "close")
    date_field = field_mapping.get("date_field", "date")
    symbol_field = field_mapping.get("symbol_field", "symbol")
    exchange_field = field_mapping.get("exchange_field", "exchange")
    
    short_period = fields.get("short_period", 5)
    long_period = fields.get("long_period", 20)
    cross_type = fields.get("cross_type", "golden")
    
    if not data:
        return {"passed_symbols": [], "failed_symbols": symbols or [], "symbol_results": [], "values": [], "result": False}
    
    grouped_data: Dict[str, List[Dict[str, Any]]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    
    for row in data:
        sym = row.get(symbol_field, "UNKNOWN")
        if sym not in grouped_data:
            grouped_data[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        grouped_data[sym].append(row)
    
    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in grouped_data.keys()]
    
    passed, failed, symbol_results, values = [], [], [], []
    
    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else symbol_exchange_map.get(symbol, "UNKNOWN")
        sym_dict = {"exchange": exchange, "symbol": symbol}
        
        symbol_data = sorted(grouped_data.get(symbol, []), key=lambda x: x.get(date_field, ""))
        prices = [float(row.get(close_field, 0)) for row in symbol_data if row.get(close_field)]
        
        if len(prices) < long_period + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data"})
            continue
        
        short_ma_series = calculate_sma_series(prices, short_period)
        long_ma_series = calculate_sma_series(prices, long_period)
        current_short_ma = short_ma_series[-1] if short_ma_series else 0
        current_long_ma = long_ma_series[-1] if long_ma_series else 0
        
        is_bullish = current_short_ma > current_long_ma
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "short_ma": round(current_short_ma, 4), "long_ma": round(current_long_ma, 4),
            "status": "bullish" if is_bullish else "bearish",
        })
        
        # time_series 생성 (signal, side 포함)
        time_series = []
        ma_start_idx = long_period - 1
        for i in range(ma_start_idx, len(symbol_data)):
            row = symbol_data[i]
            short_idx = i - (long_period - short_period)
            short_ma = short_ma_series[short_idx] if 0 <= short_idx < len(short_ma_series) else 0
            long_ma = long_ma_series[i - ma_start_idx] if i - ma_start_idx < len(long_ma_series) else 0
            
            # signal, side 결정 (크로스 감지)
            signal = None
            side = "long"
            if i > ma_start_idx:
                prev_short = short_ma_series[short_idx - 1] if 0 <= short_idx - 1 < len(short_ma_series) else 0
                prev_long = long_ma_series[i - ma_start_idx - 1] if i - ma_start_idx - 1 < len(long_ma_series) else 0
                # 골든 크로스: 단기가 장기를 상향 돌파
                if prev_short <= prev_long and short_ma > long_ma:
                    signal = "buy"
                    side = "long"
                # 데드 크로스: 단기가 장기를 하향 돌파
                elif prev_short >= prev_long and short_ma < long_ma:
                    signal = "sell"
                    side = "long"
            
            time_series.append({
                "date": row.get(date_field, ""),
                "close": row.get(close_field),
                "short_ma": round(short_ma, 4),
                "long_ma": round(long_ma, 4),
                "signal": signal,
                "side": side,
            })
        
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})
        
        if (cross_type == "golden" and is_bullish) or (cross_type == "dead" and not is_bullish):
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)
    
    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {"indicator": "MovingAverageCross", "short_period": short_period, "long_period": long_period, "cross_type": cross_type},
    }


__all__ = ["ma_cross_condition", "calculate_sma", "calculate_sma_series", "detect_crossover", "MA_CROSS_SCHEMA"]
