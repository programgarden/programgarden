"""
ProgramGarden - Registry Tools

노드 타입 및 플러그인 레지스트리 조회 도구
"""

from typing import Optional, List, Dict, Any


def list_node_types(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    사용 가능한 노드 타입 목록 조회

    Args:
        category: 카테고리 필터 (infra, realtime, data, symbol, trigger,
                  condition, risk, order, event, display, group)

    Returns:
        노드 타입 스키마 목록

    Example:
        >>> list_node_types("condition")
        [{"node_type": "ConditionNode", ...}, {"node_type": "LogicNode", ...}]
    """
    from programgarden_core import NodeTypeRegistry

    registry = NodeTypeRegistry()
    schemas = registry.list_schemas(category=category)

    return [schema.model_dump() for schema in schemas]


def get_node_schema(node_type: str) -> Optional[Dict[str, Any]]:
    """
    특정 노드 타입의 상세 스키마 조회

    Args:
        node_type: 노드 타입명 (예: ConditionNode, BrokerNode)

    Returns:
        노드 스키마 또는 None

    Example:
        >>> get_node_schema("ConditionNode")
        {"node_type": "ConditionNode", "category": "condition", "inputs": [...], ...}
    """
    from programgarden_core import NodeTypeRegistry

    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type)

    return schema.model_dump() if schema else None


def list_plugins(
    category: Optional[str] = None,
    product: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    사용 가능한 플러그인 목록 조회

    Args:
        category: 플러그인 카테고리 필터
                  (strategy_condition, new_order, modify_order, cancel_order)
        product: 상품 유형 필터 (overseas_stock, overseas_futures)

    Returns:
        플러그인 스키마 목록

    Example:
        >>> list_plugins("strategy_condition", "overseas_stock")
        [{"id": "RSI", ...}, {"id": "MACD", ...}, ...]
    """
    from programgarden_core import PluginRegistry
    from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

    registry = PluginRegistry()

    cat = PluginCategory(category) if category else None
    prod = ProductType(product) if product else None

    schemas = registry.list_plugins(category=cat, product=prod)

    return [schema.model_dump() for schema in schemas]


def get_plugin_schema(plugin_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    특정 플러그인의 상세 스키마 조회

    Args:
        plugin_id: 플러그인 ID (예: RSI, MarketOrder)
        version: 버전 (생략 시 최신 버전)

    Returns:
        플러그인 스키마 또는 None

    Example:
        >>> get_plugin_schema("RSI")
        {"id": "RSI", "params_schema": {"period": {"type": "int"}, ...}, ...}
    """
    from programgarden_core import PluginRegistry

    registry = PluginRegistry()
    schema = registry.get_schema(plugin_id, version)

    return schema.model_dump() if schema else None


def list_categories() -> List[Dict[str, Any]]:
    """
    노드 카테고리 목록 조회

    Returns:
        카테고리 정보 목록 (이름, 노드 수, 설명)

    Example:
        >>> list_categories()
        [{"category": "infra", "count": 2, "description": "INFRA"}, ...]
    """
    from programgarden_core import NodeTypeRegistry

    registry = NodeTypeRegistry()
    return registry.list_categories()
