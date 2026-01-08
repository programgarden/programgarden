"""
ProgramGarden Core - Registry 정의

Registry Layer:
- NodeTypeRegistry: 노드 타입 스키마 레지스트리
- PluginRegistry: 플러그인 스키마 레지스트리
- CredentialTypeRegistry: Credential 타입 레지스트리
- CredentialStore: Credential 저장소
"""

from programgarden_core.registry.node_registry import NodeTypeRegistry, NodeTypeSchema
from programgarden_core.registry.plugin_registry import PluginRegistry, PluginSchema
from programgarden_core.registry.credential_registry import (
    CredentialTypeRegistry,
    CredentialStore,
    MemoryCredentialStore,
    JsonFileCredentialStore,
    get_credential_type_registry,
    get_credential_store,
    set_credential_store,
)

__all__ = [
    "NodeTypeRegistry",
    "NodeTypeSchema",
    "PluginRegistry",
    "PluginSchema",
    # Credential
    "CredentialTypeRegistry",
    "CredentialStore",
    "MemoryCredentialStore",
    "JsonFileCredentialStore",
    "get_credential_type_registry",
    "get_credential_store",
    "set_credential_store",
]
