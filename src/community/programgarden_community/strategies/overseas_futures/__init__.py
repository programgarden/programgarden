"""
해외선물 실전 전략 (예정)
"""

from typing import Optional, List


def get_strategy(name: str) -> Optional[dict]:
    """전략 조회"""
    return None  # 추후 구현


def list_strategies() -> List[str]:
    """전략 목록"""
    return []  # 추후 구현


__all__ = ["get_strategy", "list_strategies"]
