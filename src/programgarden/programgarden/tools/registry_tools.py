"""
ProgramGarden - Registry Tools

Node type and plugin registry query tools
"""

from typing import Optional, List, Dict, Any


def list_node_types(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List available node types

    Args:
        category: Category filter (infra, realtime, data, symbol, trigger,
                  condition, risk, order, event, display, group)

    Returns:
        List of node type schemas

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
    Get detailed schema for a specific node type

    Args:
        node_type: Node type name (e.g., ConditionNode, BrokerNode)

    Returns:
        Node schema or None

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
    List available plugins

    Args:
        category: Plugin category filter (technical, position)
        product: Product type filter (overseas_stock, overseas_futures)

    Returns:
        List of plugin schemas

    Example:
        >>> list_plugins("technical", "overseas_stock")
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
    Get detailed schema for a specific plugin

    Args:
        plugin_id: Plugin ID (e.g., RSI, MarketOrder)
        version: Version (latest if omitted)

    Returns:
        Plugin schema or None

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
    List node categories

    Returns:
        List of category info (name, count, description)

    Example:
        >>> list_categories()
        [{"category": "infra", "count": 2, "description": "INFRA"}, ...]
    """
    from programgarden_core import NodeTypeRegistry

    registry = NodeTypeRegistry()
    return registry.list_categories()
