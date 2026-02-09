"""
ProgramGarden - Registry Tools

Node type and plugin registry query tools
"""

from typing import Optional, List, Dict, Any


def list_node_types(
    category: Optional[str] = None,
    locale: Optional[str] = None,
    include_dynamic: bool = True,
) -> List[Dict[str, Any]]:
    """
    List available node types

    Args:
        category: Category filter (infra, realtime, data, symbol, trigger,
                  condition, risk, order, event, display, group)
        locale: Locale for i18n translation (e.g., "ko", "en"). If None, returns i18n keys.
        include_dynamic: Include dynamic (Dynamic_) nodes from DynamicNodeRegistry (default True)

    Returns:
        List of node type schemas

    Example:
        >>> list_node_types("condition")
        [{"node_type": "ConditionNode", "display_name": "i18n:nodes.ConditionNode.name", ...}]
        >>> list_node_types("condition", locale="ko")
        [{"node_type": "ConditionNode", "display_name": "조건 노드", ...}]
    """
    from programgarden_core import NodeTypeRegistry, DynamicNodeRegistry

    registry = NodeTypeRegistry()
    schemas = registry.list_schemas(category=category, locale=locale)
    result = [schema.model_dump() for schema in schemas]

    if include_dynamic:
        dynamic_registry = DynamicNodeRegistry()
        for schema in dynamic_registry.list_schemas():
            if category and schema.category != category:
                continue
            schema_dict = schema.model_dump()
            schema_dict["is_dynamic"] = True
            result.append(schema_dict)

    return result


def get_node_schema(node_type: str, locale: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed schema for a specific node type

    Args:
        node_type: Node type name (e.g., ConditionNode, BrokerNode, Dynamic_MyRSI)
        locale: Locale for i18n translation (e.g., "ko", "en"). If None, returns i18n keys.

    Returns:
        Node schema or None

    Example:
        >>> get_node_schema("ConditionNode")
        {"node_type": "ConditionNode", "display_name": "i18n:nodes.ConditionNode.name", ...}
        >>> get_node_schema("Dynamic_MyRSI")
        {"node_type": "Dynamic_MyRSI", "is_dynamic": True, ...}
    """
    from programgarden_core import NodeTypeRegistry, DynamicNodeRegistry

    registry = NodeTypeRegistry()
    schema = registry.get_schema(node_type, locale=locale)
    if schema:
        return schema.model_dump()

    # 동적 노드에서 조회
    dynamic_registry = DynamicNodeRegistry()
    dynamic_schema = dynamic_registry.get_schema(node_type)
    if dynamic_schema:
        result = dynamic_schema.model_dump()
        result["is_dynamic"] = True
        return result

    return None


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


def list_categories(locale: Optional[str] = None, include_dynamic: bool = True) -> List[Dict[str, Any]]:
    """
    List node categories

    Args:
        locale: Locale for i18n translation (e.g., "ko", "en"). If None, returns raw category names.
        include_dynamic: Include dynamic (Dynamic_) nodes in category counts (default True)

    Returns:
        List of category info (id, name, description, count)

    Example:
        >>> list_categories()
        [{"id": "infra", "name": "INFRA", "count": 2, "description": ""}, ...]
        >>> list_categories(locale="ko")
        [{"id": "infra", "name": "인프라", "count": 2, "description": "워크플로우 기본 구성"}, ...]
    """
    from programgarden_core import NodeTypeRegistry, DynamicNodeRegistry

    registry = NodeTypeRegistry()
    categories = registry.list_categories(locale=locale)

    if include_dynamic:
        dynamic_registry = DynamicNodeRegistry()
        for schema in dynamic_registry.list_schemas():
            cat = schema.category
            found = False
            for cat_info in categories:
                if cat_info["id"] == cat:
                    cat_info["count"] += 1
                    found = True
                    break
            if not found:
                categories.append({
                    "id": cat,
                    "name": cat,
                    "description": "",
                    "count": 1,
                })

    return categories
