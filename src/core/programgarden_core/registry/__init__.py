"""
ProgramGarden Core - Registry 정의

Registry Layer:
- NodeTypeRegistry: 노드 타입 스키마 레지스트리
- PluginRegistry: 플러그인 스키마 레지스트리
"""

from programgarden_core.registry.node_registry import NodeTypeRegistry, NodeTypeSchema
from programgarden_core.registry.plugin_registry import PluginRegistry, PluginSchema

__all__ = [
    "NodeTypeRegistry",
    "NodeTypeSchema",
    "PluginRegistry",
    "PluginSchema",
]
