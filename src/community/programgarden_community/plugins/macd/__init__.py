"""
MACD (Moving Average Convergence Divergence) 플러그인

입력 형식 (ConditionNode와 통일):
- data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
- fields: {fast_period, slow_period, signal_period, signal_type}
- field_mapping: {close_field, date_field, symbol_field, exchange_field}
- symbols: [{exchange, symbol}, ...]

출력 형식:
- passed_symbols: [{exchange, symbol}, ...]
- failed_symbols: [{exchange, symbol}, ...]
- symbol_results: [{symbol, exchange, macd, signal, histogram}, ...]
- values: [{symbol, exchange, time_series: [{date, macd, signal, histogram, ...}, ...]}, ...]
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MACD_SCHEMA = PluginSchema(
    id="MACD",
    name="MACD (Moving Average Convergence Divergence)",
    category=PluginCategory.TECHNICAL,
    version="3.0.0",
    description="Finds trend reversal points through crossovers of short and long moving averages. Bullish when MACD crosses above signal line, bearish when crossing below.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "fast_period": {
            "type": "int",
            "default": 12,
            "title": "Fast EMA Period",
            "ge": 2,
        },
        "slow_period": {
            "type": "int",
            "default": 26,
            "title": "Slow EMA Period",
            "ge": 5,
        },
        "signal_period": {
            "type": "int",
            "default": 9,
            "title": "Signal Period",
            "ge": 2,
        },
        "signal_type": {
            "type": "string",
            "default": "bullish_cross",
            "title": "Signal Type",
            "enum": ["bullish_cross", "bearish_cross"],
        },
    },
    required_data=["data"],
    # items { from, extract } 필수 필드 (v3.0.0+)
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["trend", "momentum"],
    locales={
        "ko": {
            "name": "MACD (이동평균 수렴확산)",
            "description": "단기와 장기 이동평균의 교차를 통해 추세 전환점을 찾습니다. MACD 선이 신호선을 위로 돌파하면 상승 신호, 아래로 돌파하면 하락 신호로 해석합니다.",
            "fields.fast_period": "빠른 EMA 기간",
            "fields.slow_period": "느린 EMA 기간",
            "fields.signal_period": "신호 기간",
            "fields.signal_type": "신호 유형",
        },
    },
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


def calculate_macd_series(prices: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9) -> List[dict]:
    """
    MACD 시계열 계산 (time_series용)
    
    Returns:
        [{"macd": float, "signal": float, "histogram": float}, ...]
    """
    if len(prices) < slow + signal_period:
        return []
    
    macd_values = []
    
    for i in range(slow + signal_period, len(prices) + 1):
        sub_prices = prices[:i]
        result = calculate_macd(sub_prices, fast, slow, signal_period)
        macd_values.append(result)
    
    return macd_values


async def macd_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> dict:
    """MACD 조건 평가 (새 형식: data + field_mapping)
    
    Args:
        data: 평탄화된 배열 [{date, close, symbol, exchange, ...}, ...]
        fields: {fast_period, slow_period, signal_period, signal_type}
        field_mapping: {close_field, date_field, symbol_field, exchange_field}
        symbols: [{exchange, symbol}, ...] (선택, data에서 자동 추출 가능)
    
    Returns:
        {"passed_symbols": [...], "failed_symbols": [...], "symbol_results": [...], "values": [...]}
    """
    # 필드 매핑 기본값
    if field_mapping is None:
        field_mapping = {}
    
    close_field = field_mapping.get("close_field", "close")
    date_field = field_mapping.get("date_field", "date")
    symbol_field = field_mapping.get("symbol_field", "symbol")
    exchange_field = field_mapping.get("exchange_field", "exchange")
    
    # 파라미터 추출
    fast = fields.get("fast_period", 12)
    slow = fields.get("slow_period", 26)
    signal_period = fields.get("signal_period", 9)
    signal_type = fields.get("signal_type", "bullish_cross")
    
    # MACD 최소 데이터 요구사항
    min_required = slow + signal_period  # 26 + 9 = 35일
    
    # 데이터가 비어있으면 상세 에러 반환
    if not data:
        # symbols가 있으면 각 종목에 에러 정보 추가
        symbol_results = []
        for sym_info in (symbols or []):
            if isinstance(sym_info, dict):
                symbol_results.append({
                    "symbol": sym_info.get("symbol", ""),
                    "exchange": sym_info.get("exchange", "UNKNOWN"),
                    "macd": 0,
                    "signal": 0,
                    "histogram": 0,
                    "error": "insufficient_data",
                    "error_detail": f"No data provided. Need at least {min_required} days. Check if HistoricalDataNode returned empty time_series.",
                })
        return {
            "passed_symbols": [],
            "failed_symbols": symbols or [],
            "symbol_results": symbol_results,
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
    
    # symbols 자동 추출 (입력이 없으면)
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
        
        # 해당 심볼의 데이터 가져오기
        symbol_data = grouped_data.get(symbol, [])
        
        # 날짜순 정렬
        symbol_data = sorted(symbol_data, key=lambda x: x.get(date_field, ""))
        
        # 종가 추출
        prices = [float(row.get(close_field, 0)) for row in symbol_data if row.get(close_field)]
        
        # MACD 최소 데이터 요구사항: slow + signal_period = 35일
        min_required = slow + signal_period
        
        if len(prices) < min_required:
            # 데이터 부족 - 상세 에러 정보 포함
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "macd": 0,
                "signal": 0,
                "histogram": 0,
                "error": "insufficient_data",
                "error_detail": f"Need {min_required} days, got {len(prices)} (raw rows: {len(symbol_data)})",
            })
            continue
        
        # MACD 계산
        macd_data = calculate_macd(prices, fast, slow, signal_period)
        macd_series = calculate_macd_series(prices, fast, slow, signal_period)
        
        # 결과 저장
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            **macd_data,
        })
        
        # time_series 구성 (OHLCV + MACD + signal/side)
        time_series = []
        macd_start_idx = slow + signal_period - 1
        for i, macd_val in enumerate(macd_series):
            bar_idx = macd_start_idx + i
            if bar_idx < len(symbol_data):
                row = symbol_data[bar_idx]
                
                # signal, side 결정 (histogram 기준)
                signal = None
                side = "long"
                hist = macd_val.get("histogram", 0)
                macd_line = macd_val.get("macd", 0)
                
                # 이전 바의 histogram과 비교하여 크로스 감지
                if i > 0:
                    prev_hist = macd_series[i-1].get("histogram", 0)
                    # bullish cross: histogram이 음수에서 양수로 전환
                    if prev_hist < 0 and hist >= 0:
                        signal = "buy"
                        side = "long"
                    # bearish cross: histogram이 양수에서 음수로 전환
                    elif prev_hist > 0 and hist <= 0:
                        signal = "sell"
                        side = "long"  # 해외주식 기본
                
                time_series.append({
                    "date": row.get(date_field, ""),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get(close_field),
                    "volume": row.get("volume"),
                    "macd": macd_val.get("macd"),
                    "macd_signal": macd_val.get("signal"),
                    "histogram": macd_val.get("histogram"),
                    "signal": signal,
                    "side": side,
                })
        
        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })
        
        # 조건 판정
        if signal_type == "bullish_cross":
            passed_condition = macd_data["histogram"] > 0 and macd_data["macd"] > 0
        else:
            passed_condition = macd_data["histogram"] < 0 and macd_data["macd"] < 0
        
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
            "indicator": "MACD",
            "fast_period": fast,
            "slow_period": slow,
            "signal_period": signal_period,
            "signal_type": signal_type,
        },
    }


__all__ = ["macd_condition", "calculate_macd", "calculate_macd_series", "MACD_SCHEMA"]
