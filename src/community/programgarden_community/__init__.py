"""
ProgramGarden Community - 전략 플러그인 및 커스텀 노드 모음

커뮤니티에서 제공하는 확장:

1. 플러그인 (기존 노드의 로직 확장)
   - strategy_condition: 조건 전략 (RSI, MACD, BollingerBands 등)
   - new_order: 신규 주문 (MarketOrder, LimitOrder 등)
   - modify_order: 정정 주문 (TrackingPrice 등)
   - cancel_order: 취소 주문 (TimeStop 등)

2. 커스텀 노드 (새로운 노드 타입)
   - messaging: 알림 노드 (TelegramNode, SlackNode 등)
"""

from programgarden_community.plugins import (
    register_all_plugins,
    get_plugin,
)
from programgarden_community.nodes_registry import (
    register_all_nodes,
    get_community_node_list,
)

__version__ = "2.0.0"

# 패키지 로드 시 플러그인 및 노드 자동 등록
register_all_plugins()
register_all_nodes()

__all__ = [
    # 플러그인 관련
    "register_all_plugins",
    "get_plugin",
    # 커스텀 노드 관련
    "register_all_nodes",
    "get_community_node_list",
]
