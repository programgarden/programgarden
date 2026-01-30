"""
Volume Spike 플러그인

거래량 급증 조건을 평가합니다.
입력: data (평탄화된 배열) + field_mapping
출력: passed_symbols, failed_symbols, symbol_results, values (time_series 포함)
"""

from typing import List, Dict, Any
from collections import defaultdict
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VOLUME_SPIKE_SCHEMA = PluginSchema(
    id="VolumeSpike",
    name="Volume Spike",
    category=PluginCategory.TECHNICAL,
    version="3.0.0",
    description="Finds stocks with significantly higher trading volume than usual. Volume spikes can signal increased interest or trend changes.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 20,
            "title": "Average Period",
            "ge": 5,
        },
        "multiplier": {
            "type": "float",
            "default": 2.0,
            "title": "Multiplier",
            "description": "Multiplier compared to average volume",
            "ge": 1.0,
        },
    },
    required_data=["data"],
    # items { from, extract } 필수 필드 (v3.0.0+)
    required_fields=["symbol", "exchange", "date", "volume"],
    optional_fields=[],
    tags=["volume"],
    locales={
        "ko": {
            "name": "거래량 급증 (Volume Spike)",
            "description": "평소보다 거래량이 크게 증가한 종목을 찾습니다. 거래량 급증은 관심 증가나 추세 변화의 신호일 수 있습니다.",
            "fields.period": "평균 기간",
            "fields.multiplier": "배수",
        },
    },
)


async def volume_spike_condition(
    data: List[Dict[str, Any]] = None,
    fields: Dict[str, Any] = None,
    field_mapping: Dict[str, str] = None,
    symbols: List[Dict[str, str]] = None,
    **kwargs,
) -> dict:
    """
    거래량 급증 조건 평가
    
    Args:
        data: 평탄화된 배열 [{date, volume, symbol, exchange, ...}, ...]
        fields: {period, multiplier}
        field_mapping: {volume_field, date_field, symbol_field, exchange_field}
        symbols: [{exchange, symbol}, ...]
    
    Returns:
        passed_symbols: [{exchange, symbol}, ...]
        failed_symbols: [{exchange, symbol}, ...]
        symbol_results: [{symbol, exchange, current_volume, avg_volume, ratio, passed}, ...]
        values: [{symbol, exchange, time_series: [{date, volume, avg_volume, ratio, spike}, ...]}, ...]
    """
    data = data or []
    fields = fields or {}
    field_mapping = field_mapping or {}
    
    period = fields.get("period", 20)
    multiplier = fields.get("multiplier", 2.0)
    
    # 필드 매핑
    volume_field = field_mapping.get("volume_field", "volume")
    symbol_field = field_mapping.get("symbol_field", "symbol")
    exchange_field = field_mapping.get("exchange_field", "exchange")
    date_field = field_mapping.get("date_field", "date")
    
    passed_symbols = []
    failed_symbols = []
    symbol_results = []
    values = []
    
    if not data:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"indicator": "VolumeSpike", "period": period, "multiplier": multiplier},
        }
    
    # data에서 종목별로 그룹화
    symbol_data_map = defaultdict(list)
    for row in data:
        if isinstance(row, dict):
            sym = row.get(symbol_field, "")
            if sym:
                symbol_data_map[sym].append(row)
    
    # symbols 정규화 (없으면 data에서 자동 추출)
    if symbols and isinstance(symbols[0], dict):
        symbol_list = symbols
    elif symbols:
        symbol_list = [{"symbol": s, "exchange": "UNKNOWN"} for s in symbols]
    else:
        symbol_list = []
        seen = set()
        for row in data:
            sym = row.get(symbol_field, "")
            if sym and sym not in seen:
                seen.add(sym)
                symbol_list.append({
                    "symbol": sym,
                    "exchange": row.get(exchange_field, "UNKNOWN"),
                })
    
    # 종목별 평가
    for sym_info in symbol_list:
        sym = sym_info["symbol"]
        exchange = sym_info.get("exchange", "UNKNOWN")
        rows = symbol_data_map.get(sym, [])
        
        if not rows:
            failed_symbols.append({"symbol": sym, "exchange": exchange})
            continue
        
        # 날짜순 정렬
        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        
        # 거래량 추출
        volumes = []
        for row in rows_sorted:
            vol = row.get(volume_field, 0)
            if isinstance(vol, (int, float)) and vol > 0:
                volumes.append(vol)
        
        if len(volumes) < 2:
            failed_symbols.append({"symbol": sym, "exchange": exchange})
            symbol_results.append({
                "symbol": sym,
                "exchange": exchange,
                "current_volume": 0,
                "avg_volume": 0,
                "ratio": 0,
                "passed": False,
            })
            continue
        
        # 현재 거래량 = 마지막 값, 평균 = 그 이전 period개
        current_volume = volumes[-1]
        history_volumes = volumes[:-1]
        
        if len(history_volumes) >= period:
            avg_volume = sum(history_volumes[-period:]) / period
        else:
            avg_volume = sum(history_volumes) / len(history_volumes)
        
        ratio = current_volume / avg_volume if avg_volume > 0 else 0
        passed = current_volume > avg_volume * multiplier
        
        symbol_results.append({
            "symbol": sym,
            "exchange": exchange,
            "current_volume": int(current_volume),
            "avg_volume": round(avg_volume, 2),
            "ratio": round(ratio, 2),
            "passed": passed,
        })
        
        if passed:
            passed_symbols.append({"symbol": sym, "exchange": exchange})
        else:
            failed_symbols.append({"symbol": sym, "exchange": exchange})
        
        # values에 시계열 데이터 포함 (DisplayNode용 + signal/side)
        time_series = []
        for i, row in enumerate(rows_sorted):
            vol = row.get(volume_field, 0)
            if i >= period:
                avg = sum([r.get(volume_field, 0) for r in rows_sorted[i-period:i]]) / period
            elif i > 0:
                avg = sum([r.get(volume_field, 0) for r in rows_sorted[:i]]) / i
            else:
                avg = vol
            
            is_spike = vol > avg * multiplier if avg > 0 else False
            
            # signal, side 결정 (거래량 급증 시 매수 신호)
            signal = "buy" if is_spike else None
            side = "long"
            
            time_series.append({
                date_field: row.get(date_field, ""),
                volume_field: vol,
                "avg_volume": round(avg, 2),
                "ratio": round(vol / avg, 2) if avg > 0 else 0,
                "spike": is_spike,
                "signal": signal,
                "side": side,
            })
        
        values.append({
            "symbol": sym,
            "exchange": exchange,
            "time_series": time_series,
        })
    
    return {
        "passed_symbols": passed_symbols,
        "failed_symbols": failed_symbols,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed_symbols) > 0,
        "analysis": {
            "indicator": "VolumeSpike",
            "period": period,
            "multiplier": multiplier,
        },
    }


__all__ = ["volume_spike_condition", "VOLUME_SPIKE_SCHEMA"]

