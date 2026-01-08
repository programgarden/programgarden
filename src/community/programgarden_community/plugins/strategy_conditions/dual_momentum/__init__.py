"""
DualMomentum (듀얼 모멘텀) 플러그인

절대 모멘텀과 상대 모멘텀을 결합한 전략입니다.
- 절대 모멘텀: 자산의 과거 수익률이 양수인지 확인
- 상대 모멘텀: 기준 자산(현금, 채권 등) 대비 우수한지 확인

Gary Antonacci의 Dual Momentum 전략 기반.
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


DUAL_MOMENTUM_SCHEMA = PluginSchema(
    id="DualMomentum",
    name="듀얼 모멘텀 (Dual Momentum)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="1.0.0",
    description="절대 모멘텀 + 상대 모멘텀 결합 전략",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback_period": {
            "type": "int",
            "default": 252,
            "title": "룩백 기간",
            "description": "모멘텀 계산 기간 (거래일 기준, 252일 ≈ 12개월)",
            "ge": 20,
            "le": 504,
        },
        "absolute_threshold": {
            "type": "float",
            "default": 0.0,
            "title": "절대 모멘텀 임계값",
            "description": "절대 모멘텀 기준 수익률 (%, 기본 0 = 양수면 통과)",
            "ge": -50,
            "le": 50,
        },
        "use_relative": {
            "type": "bool",
            "default": True,
            "title": "상대 모멘텀 사용",
            "description": "True: 절대+상대, False: 절대만",
        },
        "relative_benchmark": {
            "type": "string",
            "default": "SHY",
            "title": "상대 모멘텀 벤치마크",
            "description": "비교 대상 (SHY: 미국 단기채, BIL: 초단기채)",
            "enum": ["SHY", "BIL", "CASH"],
        },
    },
    required_data=["price_data"],
    tags=["momentum", "trend", "asset_allocation"],
)


def calculate_momentum(prices: List[float], lookback: int) -> float:
    """
    모멘텀(수익률) 계산
    
    Args:
        prices: 종가 리스트 (최신이 마지막)
        lookback: 룩백 기간
    
    Returns:
        수익률 (%)
    """
    if len(prices) < lookback + 1:
        return 0.0
    
    current_price = prices[-1]
    past_price = prices[-lookback - 1] if lookback < len(prices) else prices[0]
    
    if past_price <= 0:
        return 0.0
    
    return ((current_price - past_price) / past_price) * 100


def calculate_momentum_series(prices: List[float], lookback: int) -> List[Dict[str, float]]:
    """
    모멘텀 시계열 계산 (백테스트용)
    
    Args:
        prices: 종가 리스트
        lookback: 룩백 기간
    
    Returns:
        모멘텀 시계열 [{"index": i, "momentum": value}, ...]
    """
    if len(prices) < lookback + 1:
        return []
    
    series = []
    for i in range(lookback, len(prices)):
        current = prices[i]
        past = prices[i - lookback]
        if past > 0:
            momentum = ((current - past) / past) * 100
            series.append({"index": i, "momentum": round(momentum, 2)})
    
    return series


async def dual_momentum_condition(symbols: list, price_data: dict, fields: dict) -> dict:
    """
    듀얼 모멘텀 조건 평가
    
    Args:
        symbols: 평가할 종목 리스트
        price_data: 종목별 가격 데이터
        fields: {
            "lookback_period": 252,
            "absolute_threshold": 0,
            "use_relative": True,
            "relative_benchmark": "SHY"
        }
    
    Returns:
        {
            "passed_symbols": [...],
            "failed_symbols": [...],
            "values": {...},
            "signals": [...],
            "ranking": [...]  # 모멘텀 순위
        }
    """
    lookback = fields.get("lookback_period", 252)
    threshold = fields.get("absolute_threshold", 0.0)
    use_relative = fields.get("use_relative", True)
    benchmark = fields.get("relative_benchmark", "SHY")
    
    passed = []
    failed = []
    values = {}
    signals = []
    momentum_scores = []  # 순위 계산용
    
    # 벤치마크 모멘텀 계산 (상대 모멘텀용)
    benchmark_momentum = 0.0
    if use_relative and benchmark != "CASH":
        benchmark_data = price_data.get(benchmark, {})
        if isinstance(benchmark_data, list):
            benchmark_prices = [bar.get("close", 0) for bar in benchmark_data]
        elif isinstance(benchmark_data, dict):
            benchmark_prices = benchmark_data.get("prices", [])
        else:
            benchmark_prices = []
        
        if len(benchmark_prices) >= lookback + 1:
            benchmark_momentum = calculate_momentum(benchmark_prices, lookback)
    
    for symbol in symbols:
        # 벤치마크는 스킵 (순위 계산에서 제외)
        if symbol == benchmark:
            continue
        
        symbol_data = price_data.get(symbol, {})
        
        # 가격 데이터 추출
        if isinstance(symbol_data, list):
            prices = [bar.get("close", bar.get("price", 0)) for bar in symbol_data]
            dates = [bar.get("date", "") for bar in symbol_data]
        elif isinstance(symbol_data, dict):
            prices = symbol_data.get("prices", [])
            dates = symbol_data.get("dates", [])
        else:
            prices = []
            dates = []
        
        # 데이터 부족 시 처리
        if len(prices) < lookback + 1:
            failed.append(symbol)
            values[symbol] = {
                "momentum": 0,
                "absolute_pass": False,
                "relative_pass": False,
                "status": "insufficient_data",
            }
            continue
        
        # 모멘텀 계산
        momentum = calculate_momentum(prices, lookback)
        
        # 절대 모멘텀 체크
        absolute_pass = momentum > threshold
        
        # 상대 모멘텀 체크
        relative_pass = True
        if use_relative:
            relative_pass = momentum > benchmark_momentum
        
        # 최종 판단
        passed_condition = absolute_pass and relative_pass
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
        
        # 모멘텀 스코어 저장 (순위용)
        momentum_scores.append({
            "symbol": symbol,
            "momentum": round(momentum, 2),
        })
        
        values[symbol] = {
            "momentum": round(momentum, 2),
            "benchmark_momentum": round(benchmark_momentum, 2),
            "absolute_pass": absolute_pass,
            "relative_pass": relative_pass,
            "status": "passed" if passed_condition else "failed",
        }
        
        # 백테스트용 시그널 생성
        # 듀얼 모멘텀은 월간 리밸런싱이 일반적 (매월 말 체크)
        momentum_series = calculate_momentum_series(prices, lookback)
        
        # 매월 리밸런싱 시그널 (약 21거래일마다)
        rebalance_interval = 21
        prev_signal = None
        
        for i, mom_data in enumerate(momentum_series):
            if i % rebalance_interval != 0:
                continue
            
            idx = mom_data["index"]
            mom = mom_data["momentum"]
            
            current_signal = "buy" if mom > threshold else "sell"
            
            # 신호 변경 시에만 시그널 생성
            if current_signal != prev_signal:
                if idx < len(dates) and dates:
                    signals.append({
                        "date": dates[idx],
                        "symbol": symbol,
                        "signal": current_signal,
                        "action": current_signal,
                        "price": prices[idx] if idx < len(prices) else 0,
                        "momentum": mom,
                    })
                prev_signal = current_signal
    
    # 모멘텀 순위 계산 (상대 모멘텀)
    ranking = sorted(momentum_scores, key=lambda x: x["momentum"], reverse=True)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "values": values,
        "result": len(passed) > 0,
        "signals": signals,
        "ranking": ranking,
        "analysis": {
            "indicator": "DualMomentum",
            "lookback_period": lookback,
            "absolute_threshold": threshold,
            "use_relative": use_relative,
            "benchmark": benchmark,
            "benchmark_momentum": round(benchmark_momentum, 2),
            "description": f"{lookback}일 모멘텀 > {threshold}% & 벤치마크({benchmark})",
        },
    }


__all__ = [
    "dual_momentum_condition",
    "calculate_momentum",
    "calculate_momentum_series",
    "DUAL_MOMENTUM_SCHEMA",
]
