"""
해외주식 실전 전략

LS증권 해외주식 API를 사용하는 실전 전략 모음입니다.

전략 목록:
- (준비 중)
"""

from typing import Optional, List


_STRATEGIES = {}


def _load_strategies():
    """전략 lazy loading"""
    global _STRATEGIES
    # 전략이 추가되면 여기에 import
    pass


def get_strategy(name: str) -> Optional[dict]:
    """전략 조회"""
    _load_strategies()
    return _STRATEGIES.get(name)


def list_strategies() -> List[str]:
    """전략 목록"""
    _load_strategies()
    return list(_STRATEGIES.keys())


__all__ = ["get_strategy", "list_strategies"]
