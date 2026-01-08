"""
MovingAverageCross (이동평균선 크로스) 플러그인

골든크로스/데드크로스 조건을 평가합니다.
- 골든크로스: 단기 MA가 장기 MA를 상향 돌파 → 매수 신호
- 데드크로스: 단기 MA가 장기 MA를 하향 돌파 → 매도 신호
"""

from typing import List, Dict, Any
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MA_CROSS_SCHEMA = PluginSchema(
    id="MovingAverageCross",
    name="이동평균선 크로스 (Golden/Dead Cross)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="단기/장기 이동평균선 크로스오버 조건",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "short_period": {
            "type": "int",
            "default": 5,
            "title": "단기 MA 기간",
            "description": "단기 이동평균선 기간 (일)",
            "ge": 2,
            "le": 50,
        },
        "long_period": {
            "type": "int",
            "default": 20,
            "title": "장기 MA 기간",
            "description": "장기 이동평균선 기간 (일)",
            "ge": 5,
            "le": 200,
        },
        "cross_type": {
            "type": "string",
            "default": "golden",
            "title": "크로스 유형",
            "description": "golden: 골든크로스(매수), dead: 데드크로스(매도)",
            "enum": ["golden", "dead"],
        },
    },
    required_data=["price_data"],
    tags=["trend", "moving_average", "crossover"],
)


def calculate_sma(prices: List[float], period: int) -> float:
    """
    단순 이동평균(SMA) 계산
    
    Args:
        prices: 종가 리스트 (최신이 마지막)
        period: 이동평균 기간
    
    Returns:
        SMA 값
    """
    if len(prices) < period:
        return prices[-1] if prices else 0
    
    return sum(prices[-period:]) / period


def calculate_sma_series(prices: List[float], period: int) -> List[float]:
    """
    SMA 시계열 계산 (백테스트용)
    
    Args:
        prices: 종가 리스트
        period: 이동평균 기간
    
    Returns:
        SMA 시계열 리스트 (길이: len(prices) - period + 1)
    """
    if len(prices) < period:
        return []
    
    sma_values = []
    for i in range(period - 1, len(prices)):
        sma = sum(prices[i - period + 1:i + 1]) / period
        sma_values.append(sma)
    
    return sma_values


def detect_crossover(
    short_ma: List[float],
    long_ma: List[float],
    cross_type: str = "golden",
) -> List[int]:
    """
    크로스오버 시점 감지
    
    Args:
        short_ma: 단기 MA 시계열
        long_ma: 장기 MA 시계열
        cross_type: "golden" (상향돌파) 또는 "dead" (하향돌파)
    
    Returns:
        크로스 발생 인덱스 리스트
    """
    # 두 시계열 길이 맞추기
    min_len = min(len(short_ma), len(long_ma))
    short_ma = short_ma[-min_len:]
    long_ma = long_ma[-min_len:]
    
    crossover_indices = []
    
    for i in range(1, min_len):
        prev_short = short_ma[i - 1]
        prev_long = long_ma[i - 1]
        curr_short = short_ma[i]
        curr_long = long_ma[i]
        
        if cross_type == "golden":
            # 골든크로스: 단기MA가 장기MA를 상향 돌파
            if prev_short <= prev_long and curr_short > curr_long:
                crossover_indices.append(i)
        else:  # dead
            # 데드크로스: 단기MA가 장기MA를 하향 돌파
            if prev_short >= prev_long and curr_short < curr_long:
                crossover_indices.append(i)
    
    return crossover_indices


async def ma_cross_condition(symbols: list, price_data: dict, fields: dict) -> dict:
    """
    이동평균선 크로스 조건 평가
    
    Args:
        symbols: 평가할 종목 리스트
        price_data: 종목별 가격 데이터 {"AAPL": {"prices": [...]} 또는 OHLCV 리스트}
        fields: {"short_period": 5, "long_period": 20, "cross_type": "golden"}
    
    Returns:
        {
            "passed_symbols": [...],
            "failed_symbols": [...],
            "values": {...},
            "result": bool,
            "signals": [...]  # 백테스트용 시그널 리스트
        }
    """
    short_period = fields.get("short_period", 5)
    long_period = fields.get("long_period", 20)
    cross_type = fields.get("cross_type", "golden")
    
    passed = []
    failed = []
    values = {}
    signals = []  # 백테스트용 시그널
    
    for symbol in symbols:
        symbol_data = price_data.get(symbol, {})
        
        # 가격 데이터 추출 (다양한 형식 지원)
        if isinstance(symbol_data, list):
            # OHLCV 리스트 형식
            prices = [bar.get("close", bar.get("price", 0)) for bar in symbol_data]
            dates = [bar.get("date", "") for bar in symbol_data]
        elif isinstance(symbol_data, dict):
            prices = symbol_data.get("prices", [])
            dates = symbol_data.get("dates", [])
        else:
            prices = []
            dates = []
        
        # 데이터 부족 시 처리
        if len(prices) < long_period + 1:
            failed.append(symbol)
            values[symbol] = {
                "short_ma": 0,
                "long_ma": 0,
                "ma_gap": 0,
                "status": "insufficient_data",
            }
            continue
        
        # MA 계산
        short_ma_series = calculate_sma_series(prices, short_period)
        long_ma_series = calculate_sma_series(prices, long_period)
        
        # 현재 MA 값
        current_short_ma = short_ma_series[-1] if short_ma_series else 0
        current_long_ma = long_ma_series[-1] if long_ma_series else 0
        ma_gap = ((current_short_ma - current_long_ma) / current_long_ma * 100) if current_long_ma > 0 else 0
        
        # 크로스오버 감지 (백테스트용)
        crossover_indices = detect_crossover(short_ma_series, long_ma_series, cross_type)
        
        # 시그널 생성 (백테스트용)
        # long_ma_series의 시작 인덱스 = long_period - 1
        offset = long_period - 1
        for idx in crossover_indices:
            actual_idx = offset + idx
            if actual_idx < len(dates) and dates:
                signal_action = "buy" if cross_type == "golden" else "sell"
                signals.append({
                    "date": dates[actual_idx],
                    "symbol": symbol,
                    "signal": signal_action,
                    "action": signal_action,
                    "price": prices[actual_idx] if actual_idx < len(prices) else 0,
                    "short_ma": short_ma_series[idx] if idx < len(short_ma_series) else 0,
                    "long_ma": long_ma_series[idx] if idx < len(long_ma_series) else 0,
                })
        
        # 현재 상태 판단 (실시간용)
        is_bullish = current_short_ma > current_long_ma
        current_status = "bullish" if is_bullish else "bearish"
        
        # 조건 통과 여부 (실시간: 현재 상태 기준)
        if cross_type == "golden":
            passed_condition = is_bullish
        else:
            passed_condition = not is_bullish
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
        
        values[symbol] = {
            "short_ma": round(current_short_ma, 4),
            "long_ma": round(current_long_ma, 4),
            "ma_gap": round(ma_gap, 2),
            "status": current_status,
            "crossover_count": len(crossover_indices),
        }
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "signals": signals,
        "analysis": {
            "indicator": "MovingAverageCross",
            "short_period": short_period,
            "long_period": long_period,
            "cross_type": cross_type,
            "description": f"MA{short_period} {'>' if cross_type == 'golden' else '<'} MA{long_period}",
        },
    }


__all__ = ["ma_cross_condition", "calculate_sma", "calculate_sma_series", "detect_crossover", "MA_CROSS_SCHEMA"]
