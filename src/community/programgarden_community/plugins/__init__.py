"""
ProgramGarden Community - 플러그인 레지스트리

플러그인 자동 로딩 및 등록을 담당합니다.
폴더 구조:
    plugins/
    ├── strategy_conditions/     # 전략 조건 (ConditionNode용)
    ├── new_order_conditions/    # 신규 주문 (NewOrderNode용)
    ├── modify_order_conditions/ # 정정 주문 (ModifyOrderNode용)
    └── cancel_order_conditions/ # 취소 주문 (CancelOrderNode용)

사용법:
    from programgarden_community.plugins import register_all_plugins, get_plugin
    
    register_all_plugins()
    schema = get_plugin("RSI")
"""

from typing import Optional, Dict, Any
from pathlib import Path
from importlib import import_module


def register_all_plugins() -> None:
    """
    모든 플러그인을 PluginRegistry에 등록합니다.
    
    각 카테고리 폴더를 스캔하여 플러그인을 자동 등록합니다.
    """
    from programgarden_core.registry import PluginRegistry
    
    # 각 카테고리별 등록 함수 호출
    from .strategy_conditions import register_strategy_condition_plugins
    from .new_order_conditions import register_new_order_plugins
    from .modify_order_conditions import register_modify_order_plugins
    from .cancel_order_conditions import register_cancel_order_plugins
    
    register_strategy_condition_plugins()
    register_new_order_plugins()
    register_modify_order_plugins()
    register_cancel_order_plugins()


def get_plugin(plugin_id: str) -> Optional[Dict[str, Any]]:
    """
    플러그인 스키마 조회
    
    Args:
        plugin_id: 플러그인 ID (예: "RSI", "MACD")
    
    Returns:
        플러그인 스키마 dict 또는 None
    """
    from programgarden_core.registry import PluginRegistry
    
    registry = PluginRegistry()
    schema = registry.get_schema(plugin_id)
    
    if schema:
        return {
            "id": schema.id,
            "name": schema.name,
            "category": schema.category.value if hasattr(schema.category, 'value') else schema.category,
            "version": schema.version,
            "description": schema.description,
            "products": [p.value if hasattr(p, 'value') else p for p in schema.products],
            "fields_schema": schema.fields_schema,
            "required_data": schema.required_data,
            "tags": schema.tags,
        }
    return None


def list_plugins(
    category: Optional[str] = None,
    product: Optional[str] = None,
) -> Dict[str, list]:
    """
    플러그인 목록 조회
    
    Args:
        category: 필터링할 카테고리 (strategy_condition, new_order 등)
        product: 필터링할 상품 (overseas_stock, overseas_futures 등)
    
    Returns:
        카테고리별 플러그인 ID 목록
    """
    from programgarden_core.registry import PluginRegistry
    
    registry = PluginRegistry()
    return registry.list_plugins(category=category, product=product)


__all__ = [
    "register_all_plugins",
    "get_plugin",
    "list_plugins",
]
