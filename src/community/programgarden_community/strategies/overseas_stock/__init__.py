"""
해외주식 실전 전략

LS증권 해외주식 API를 사용하는 실전 전략 모음입니다.

전략 목록:
- penny_stock_rsi: 동전주 RSI 과매도 매수 전략
- backtest_to_live: 백테스트 → 성과 검증 → 실전 배포
- realtime_risk_monitor: 실시간 수익률 계산 + 위험관리
"""

from typing import Optional, List


_STRATEGIES = {}


def _load_strategies():
    """전략 lazy loading"""
    global _STRATEGIES
    if not _STRATEGIES:
        from .penny_stock_rsi import PENNY_STOCK_RSI
        from .backtest_to_live import BACKTEST_TO_LIVE
        from .realtime_risk_monitor import REALTIME_RISK_MONITOR
        
        _STRATEGIES = {
            "penny_stock_rsi": PENNY_STOCK_RSI,
            "backtest_to_live": BACKTEST_TO_LIVE,
            "realtime_risk_monitor": REALTIME_RISK_MONITOR,
        }


def get_strategy(name: str) -> Optional[dict]:
    """전략 조회"""
    _load_strategies()
    return _STRATEGIES.get(name)


def list_strategies() -> List[str]:
    """전략 목록"""
    _load_strategies()
    return list(_STRATEGIES.keys())


__all__ = ["get_strategy", "list_strategies"]
