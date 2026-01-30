"""
DualMomentum (듀얼 모멘텀) 플러그인

입력 형식 (ConditionNode와 통일):
- data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
- fields: {lookback_period, absolute_threshold, use_relative, relative_benchmark}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}
- symbols: [{exchange, symbol}, ...]

Gary Antonacci의 Dual Momentum 전략 기반.
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


DUAL_MOMENTUM_SCHEMA = PluginSchema(
    id="DualMomentum",
    name="Dual Momentum",
    category=PluginCategory.TECHNICAL,
    version="3.0.0",
    description="Combines absolute momentum (recent returns) and relative momentum (vs benchmark). Invests in stocks with strong upward trends.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback_period": {"type": "int", "default": 252, "title": "Lookback Period"},
        "absolute_threshold": {"type": "float", "default": 0.0, "title": "Absolute Threshold (%)"},
        "use_relative": {"type": "bool", "default": True, "title": "Use Relative Momentum"},
        "relative_benchmark": {"type": "string", "default": "SHY", "enum": ["SHY", "BIL", "CASH"], "title": "Benchmark"},
    },
    required_data=["data"],
    # items { from, extract } 필수 필드 (v3.0.0+)
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["momentum", "trend", "asset_allocation"],
    locales={
        "ko": {
            "name": "듀얼 모멘텀 (Dual Momentum)",
            "description": "절대 모멘텀(최근 수익률)과 상대 모멘텀(벤치마크 대비 성과)을 결합한 전략입니다. 상승세가 강한 종목에 투자합니다.",
            "fields.lookback_period": "룩백 기간",
            "fields.absolute_threshold": "절대 모멘텀 임계값 (%)",
            "fields.use_relative": "상대 모멘텀 사용",
            "fields.relative_benchmark": "벤치마크",
        },
    },
)


def calculate_momentum(prices: List[float], lookback: int) -> float:
    if len(prices) < lookback + 1:
        return 0.0
    current_price = prices[-1]
    past_price = prices[-lookback - 1] if lookback < len(prices) else prices[0]
    if past_price <= 0:
        return 0.0
    return ((current_price - past_price) / past_price) * 100


async def dual_momentum_condition(
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
    
    lookback = fields.get("lookback_period", 252)
    threshold = fields.get("absolute_threshold", 0.0)
    use_relative = fields.get("use_relative", True)
    benchmark = fields.get("relative_benchmark", "SHY")
    
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
    
    # 벤치마크 모멘텀 계산
    benchmark_momentum = 0.0
    if use_relative and benchmark != "CASH" and benchmark in grouped_data:
        bm_data = sorted(grouped_data[benchmark], key=lambda x: x.get(date_field, ""))
        bm_prices = [float(row.get(close_field, 0)) for row in bm_data if row.get(close_field)]
        if len(bm_prices) >= lookback + 1:
            benchmark_momentum = calculate_momentum(bm_prices, lookback)
    
    passed, failed, symbol_results, values, momentum_scores = [], [], [], [], []
    
    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else symbol_exchange_map.get(symbol, "UNKNOWN")
        sym_dict = {"exchange": exchange, "symbol": symbol}
        
        if symbol == benchmark:
            continue
        
        symbol_data = sorted(grouped_data.get(symbol, []), key=lambda x: x.get(date_field, ""))
        prices = [float(row.get(close_field, 0)) for row in symbol_data if row.get(close_field)]
        
        if len(prices) < lookback + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data"})
            continue
        
        momentum = calculate_momentum(prices, lookback)
        absolute_pass = momentum > threshold
        relative_pass = (not use_relative) or (momentum > benchmark_momentum)
        passed_condition = absolute_pass and relative_pass
        
        momentum_scores.append({"symbol": symbol, "momentum": round(momentum, 2)})
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "momentum": round(momentum, 2), "benchmark_momentum": round(benchmark_momentum, 2),
            "absolute_pass": absolute_pass, "relative_pass": relative_pass,
            "status": "passed" if passed_condition else "failed",
        })
        
        # time_series 생성 (signal, side 포함)
        # 마지막 바에만 signal 추가 (모멘텀 전략은 주기적 리밸런싱)
        time_series = []
        if symbol_data:
            last_row = symbol_data[-1]
            signal = "buy" if passed_condition else None
            side = "long"
            time_series.append({
                "date": last_row.get(date_field, ""),
                "close": last_row.get(close_field),
                "momentum": round(momentum, 2),
                "signal": signal,
                "side": side,
            })
        
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})
        
        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)
    
    ranking = sorted(momentum_scores, key=lambda x: x["momentum"], reverse=True)
    
    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0, "ranking": ranking,
        "analysis": {"indicator": "DualMomentum", "lookback_period": lookback, "threshold": threshold, "benchmark": benchmark},
    }


__all__ = ["dual_momentum_condition", "calculate_momentum", "DUAL_MOMENTUM_SCHEMA"]
