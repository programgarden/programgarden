"""
ProgramGarden Community - 커뮤니티 노드 등록

커뮤니티에서 기여한 커스텀 노드를 NodeTypeRegistry에 등록합니다.
프로그램 시작 시 register_all_nodes()를 호출하면 커뮤니티 노드가 사용 가능해집니다.

사용 예시:
    from programgarden_community.nodes_registry import register_all_nodes
    register_all_nodes()
    
    # 이후 워크플로우에서 TelegramNode 사용 가능
    {
        "nodes": [
            {"id": "notify", "type": "TelegramNode", "chat_id": "...", ...}
        ]
    }
"""


def register_all_nodes() -> None:
    """
    모든 커뮤니티 노드를 NodeTypeRegistry에 등록
    
    등록된 노드는 워크플로우 JSON에서 type으로 참조 가능합니다.
    """
    from programgarden_core.registry import NodeTypeRegistry
    
    registry = NodeTypeRegistry()
    
    # === Messaging Nodes ===
    from programgarden_community.nodes.messaging import TelegramNode
    
    messaging_nodes = [
        TelegramNode,
        # 향후 추가: SlackNode, DiscordNode, etc.
    ]
    
    for node_class in messaging_nodes:
        try:
            registry.register_external(
                node_class,
                source="community",
                trust_level="community",
            )
        except ValueError as e:
            # 이미 등록된 경우 무시 (중복 호출 방지)
            pass


def get_community_node_list() -> list:
    """
    등록 가능한 커뮤니티 노드 목록 반환 (등록 전 확인용)
    """
    return [
        {
            "type": "TelegramNode",
            "category": "event",
            "description": "Send messages via Telegram Bot API",
            "requires_credential": True,
        },
        # 향후 추가될 노드들...
    ]
