"""
ProgramGarden Core - 모델 정의

5-Layer Architecture 모델:
- Edge: 노드 간 연결
- WorkflowDefinition: 워크플로우 정의 (Layer 3)
- WorkflowJob: 실행 인스턴스 (Layer 4)
- JobState: Job 상태 스냅샷
- BrokerCredential: 인증 정보 (Layer 2)
- Credential: n8n 스타일 credential 시스템
- Event: 이벤트 히스토리 (Layer 5)
"""

from programgarden_core.models.edge import Edge
from programgarden_core.models.workflow import WorkflowDefinition, WorkflowInput, CredentialReference
from programgarden_core.models.job import WorkflowJob, JobState, JobStatus
from programgarden_core.models.credential import (
    # Legacy
    BrokerCredential, 
    AccountInfo, 
    DBCredential, 
    DBType,
    # n8n style credential system
    Credential,
    CredentialTypeSchema,
    CredentialField,
    CredentialFieldType,
    BUILTIN_CREDENTIAL_SCHEMAS,
)
from programgarden_core.models.event import Event, EventType
from programgarden_core.models.field_binding import (
    FieldSchema,
    FieldType,
    FieldCategory,
    ExpressionMode,
    UIComponent,
    FieldValueType,
    FieldsDict,
    parse_field_value,
    is_expression,
)
from programgarden_core.models.resource import (
    ThrottleLevel,
    ResourceUsage,
    ResourceLimits,
    ThrottleState,
    ResourceHints,
    DEFAULT_NODE_HINTS,
    get_node_hints,
)
from programgarden_core.models.plugin_resource import (
    TrustLevel,
    TRUST_LEVEL_LIMITS,
    PluginResourceHints,
    DEFAULT_PLUGIN_HINTS,
    get_plugin_hints,
)
from programgarden_core.models.exchange import (
    ProductType,
    ExchangeInfo,
    ExchangeRegistry,
    exchange_registry,
    SymbolEntry,
    normalize_symbol,
    normalize_symbols,
    symbols_to_dict_list,
    extract_symbol_codes,
)

__all__ = [
    # Edge
    "Edge",
    # Workflow
    "WorkflowDefinition",
    "WorkflowInput",
    "CredentialReference",
    # Job
    "WorkflowJob",
    "JobState",
    "JobStatus",
    # Credential (Legacy)
    "BrokerCredential",
    "AccountInfo",
    "DBCredential",
    "DBType",
    # Credential (n8n style)
    "Credential",
    "CredentialTypeSchema",
    "CredentialField",
    "CredentialFieldType",
    "BUILTIN_CREDENTIAL_SCHEMAS",
    # Event
    "Event",
    "EventType",
    # Field Binding
    "FieldSchema",
    "FieldType",
    "FieldCategory",
    "ExpressionMode",
    "FieldValueType",
    "FieldsDict",
    "parse_field_value",
    "is_expression",
    # Resource Management
    "ThrottleLevel",
    "ResourceUsage",
    "ResourceLimits",
    "ThrottleState",
    "ResourceHints",
    "DEFAULT_NODE_HINTS",
    "get_node_hints",
    # Plugin Resource
    "TrustLevel",
    "TRUST_LEVEL_LIMITS",
    "PluginResourceHints",
    "DEFAULT_PLUGIN_HINTS",
    "get_plugin_hints",
    # Exchange
    "ProductType",
    "ExchangeInfo",
    "ExchangeRegistry",
    "exchange_registry",
    "SymbolEntry",
    "normalize_symbol",
    "normalize_symbols",
    "symbols_to_dict_list",
    "extract_symbol_codes",
]
