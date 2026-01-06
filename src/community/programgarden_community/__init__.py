"""
ProgramGarden Community - 전략 플러그인 모음

커뮤니티에서 제공하는 전략 플러그인:
- strategy_condition: 조건 전략 (RSI, MACD, BollingerBands 등)
- new_order: 신규 주문 (MarketOrder, LimitOrder 등)
- modify_order: 정정 주문 (TrackingPrice 등)
- cancel_order: 취소 주문 (TimeStop 등)
"""

from programgarden_community.plugins import (
    register_all_plugins,
    get_plugin,
)

__version__ = "2.0.0"

# 패키지 로드 시 플러그인 자동 등록
register_all_plugins()

__all__ = [
    "register_all_plugins",
    "get_plugin",
]
