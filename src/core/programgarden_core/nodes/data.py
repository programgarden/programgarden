"""
ProgramGarden Core - Data Nodes

Data query nodes:
- MarketDataNode: REST API market data query
- SQLiteNode: Local SQLite database
- PostgresNode: External PostgreSQL database
- HTTPRequestNode: External REST API request

계좌 조회는 account/AccountNode 참조
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class MarketDataNode(BaseNode):
    """
    REST API one-time market data query node

    Fetches market data at a specific point in time via REST API
    """

    type: Literal["MarketDataNode"] = "MarketDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.MarketDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/marketdata.svg"

    # 브로커 연결 필드 (명시적 바인딩 필수)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력

    # 종목 리스트 (직접 입력 또는 포트로 받기)
    # 거래소 정보 포함: [{"exchange": "NASDAQ", "symbol": "AAPL"}, ...]
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of symbol entries with exchange and symbol code",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        ),
        InputPort(
            name="symbols", type="symbol_list", description="i18n:ports.symbols"
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="values", type="market_data_list", description="i18n:ports.market_data_values"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode(브로커 노드)를 먼저 추가하고, 그 노드의 connection 출력을 여기에 연결하세요.",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
                ui_component=UIComponent.BINDING_INPUT,
            ),
            # === PARAMETERS: 종목 리스트 ===
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="종목 리스트. 직접 입력하거나 다른 노드에서 바인딩할 수 있습니다.",
                required=True,
                default=[],
                array_item_type=FieldType.OBJECT,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example=[{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NYSE", "symbol": "IBM"}],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=["WatchlistNode.symbols", "ScreenerNode.symbols", "MarketUniverseNode.symbols"],
                expected_type="list[{exchange: str, symbol: str}]",
                ui_component=UIComponent.SYMBOL_EDITOR,
                help_text="직접 입력 또는 바인딩 가능 (fx 토글)",
            ),
            # === FIELD MAPPING: 필드명 매핑 (symbols 바로 하단에 표시) ===
            "exchange_field": FieldSchema(
                name="exchange_field",
                type=FieldType.STRING,
                description="거래소 필드명 (바인딩 데이터의 필드명이 다를 때 매핑)",
                default="exchange",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="exchange",
                group="field_mapping",
                collapsed=True,
            ),
            "symbol_field": FieldSchema(
                name="symbol_field",
                type=FieldType.STRING,
                description="종목코드 필드명 (바인딩 데이터의 필드명이 다를 때 매핑)",
                default="symbol",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="symbol",
                group="field_mapping",
                collapsed=True,
            ),
        }


class AggregationType(str):
    """집계 함수 타입"""
    MAX = "max"
    MIN = "min"
    SUM = "sum"
    COUNT = "count"
    LAST = "last"
    FIRST = "first"
    AVG = "avg"


class SQLiteNode(BaseNode):
    """
    로컬 SQLite 데이터베이스 노드

    로컬 파일 기반 SQLite DB에 데이터를 저장/조회합니다.
    메모리 캐시 + 주기적 DB 동기화로 실시간 데이터 처리에 적합합니다.
    
    주요 용도:
    - 트레일링스탑 High Water Mark (최고점) 추적
    - 전략 상태 저장/복구 (Graceful Restart)
    - 로컬 데이터 캐싱
    
    Example config:
        {
            "db_path": "./programgarden_storage.db",
            "table": "trailing_stop_state",
            "key_fields": ["symbol"],
            "save_fields": ["symbol", "peak_price", "peak_pnl_rate", "updated_at"],
            "aggregations": {"peak_price": "max", "peak_pnl_rate": "max"},
            "sync_interval_ms": 1000,
            "sync_on_change_count": 10
        }
    """

    type: Literal["SQLiteNode"] = "SQLiteNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.SQLiteNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/sqlite.svg"

    # SQLite 설정
    db_path: str = Field(
        default="./programgarden_storage.db",
        description="SQLite DB 파일 경로",
    )
    table: str = Field(..., description="테이블 이름")
    key_fields: List[str] = Field(
        ...,
        description="Primary Key 필드 목록 (예: ['symbol'])",
    )
    save_fields: List[str] = Field(
        ...,
        description="저장할 필드 목록 (예: ['symbol', 'peak_price', 'updated_at'])",
    )

    # 집계 설정 (메모리 캐시에서 계산)
    aggregations: Optional[dict] = Field(
        default=None,
        description="필드별 집계 함수 (예: {'peak_price': 'max', 'peak_pnl_rate': 'max'})",
    )

    # 동기화 설정
    sync_interval_ms: int = Field(
        default=1000,
        description="DB 동기화 주기 (밀리초)",
    )
    sync_on_change_count: int = Field(
        default=10,
        description="변경 횟수 기준 동기화 (N번 변경 시 즉시 저장)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data_to_save",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="saved",
            type="any",
            description="i18n:ports.saved_data",
        ),
        OutputPort(
            name="loaded",
            type="any",
            description="i18n:ports.loaded_data",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 스토리지 설정 ===
            "db_path": FieldSchema(
                name="db_path",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.db_path",
                default="./programgarden_storage.db",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="./my_strategy_state.db",
                expected_type="str",
            ),
            "table": FieldSchema(
                name="table",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.table",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="trailing_stop_state",
                expected_type="str",
            ),
            "key_fields": FieldSchema(
                name="key_fields",
                type=FieldType.ARRAY,
                description="i18n:fields.SQLiteNode.key_fields",
                required=True,
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=["symbol"],
                expected_type="list[str]",
            ),
            "save_fields": FieldSchema(
                name="save_fields",
                type=FieldType.ARRAY,
                description="i18n:fields.SQLiteNode.save_fields",
                required=True,
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=["symbol", "peak_price", "peak_pnl_rate", "updated_at"],
                expected_type="list[str]",
            ),
            "aggregations": FieldSchema(
                name="aggregations",
                type=FieldType.OBJECT,
                description="i18n:fields.SQLiteNode.aggregations",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"peak_price": "max", "peak_pnl_rate": "max"},
                expected_type="dict[str, str]",
            ),
            # === SETTINGS: 동기화 설정 ===
            "sync_interval_ms": FieldSchema(
                name="sync_interval_ms",
                type=FieldType.INTEGER,
                description="i18n:fields.SQLiteNode.sync_interval_ms",
                default=1000,
                min_value=100,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=1000,
                expected_type="int",
            ),
            "sync_on_change_count": FieldSchema(
                name="sync_on_change_count",
                type=FieldType.INTEGER,
                description="i18n:fields.SQLiteNode.sync_on_change_count",
                default=10,
                min_value=1,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=10,
                expected_type="int",
            ),
        }


class PostgresNode(BaseNode):
    """
    외부 PostgreSQL 데이터베이스 노드

    외부 PostgreSQL DB에 데이터를 저장/조회합니다.
    연결 정보는 credential_id를 통해 안전하게 관리됩니다.
    
    주요 용도:
    - 분산 환경에서 상태 공유
    - 대용량 데이터 저장
    - 백테스트 결과 저장
    
    Example DSL:
        {
            "id": "db",
            "type": "PostgresNode",
            "credential_id": "my-postgres",
            "table": "trading_state",
            "key_fields": ["symbol"],
            "save_fields": ["symbol", "peak_price", "updated_at"]
        }
    """

    type: Literal["PostgresNode"] = "PostgresNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.PostgresNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/postgres.svg"

    # Credential (공통 패턴)
    credential_id: Optional[str] = Field(
        default=None,
        description="PostgreSQL credential ID",
    )

    # credential에서 자동 주입 (exclude=True)
    host: Optional[str] = Field(default=None, exclude=True)
    port: int = Field(default=5432, exclude=True)
    database: Optional[str] = Field(default=None, exclude=True)
    username: Optional[str] = Field(default=None, exclude=True)
    password: Optional[str] = Field(default=None, exclude=True)
    ssl_enabled: bool = Field(default=False, exclude=True)

    # 테이블 설정 (DSL에서 직접 지정)
    table: str = Field(..., description="테이블 이름")
    schema_name: str = Field(default="public", description="스키마 이름")
    key_fields: List[str] = Field(..., description="Primary Key 필드 목록")
    save_fields: List[str] = Field(..., description="저장할 필드 목록")

    # 집계 설정
    aggregations: Optional[dict] = Field(
        default=None,
        description="필드별 집계 함수 (예: {'peak_price': 'max'})",
    )

    # 동기화 설정
    sync_interval_ms: int = Field(default=1000, description="DB 동기화 주기 (밀리초)")
    sync_on_change_count: int = Field(default=10, description="변경 횟수 기준 동기화")
    connection_timeout: int = Field(default=30, description="연결 타임아웃 (초)")

    _inputs: List[InputPort] = [
        InputPort(name="data", type="any", description="i18n:ports.data_to_save"),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="saved", type="any", description="i18n:ports.saved_data"),
        OutputPort(name="loaded", type="any", description="i18n:ports.loaded_data"),
        OutputPort(name="query_result", type="any", description="i18n:ports.query_result"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 스토리지 설정 ===
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.PostgresNode.credential_id",
                credential_types=["postgres"],
                category=FieldCategory.PARAMETERS,
                bindable=False,
            ),
            "table": FieldSchema(
                name="table",
                type=FieldType.STRING,
                description="i18n:fields.PostgresNode.table",
                required=True,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="trading_state",
                expected_type="str",
            ),
            "schema_name": FieldSchema(
                name="schema_name",
                type=FieldType.STRING,
                description="i18n:fields.PostgresNode.schema_name",
                default="public",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="public",
                expected_type="str",
            ),
            "key_fields": FieldSchema(
                name="key_fields",
                type=FieldType.ARRAY,
                description="i18n:fields.PostgresNode.key_fields",
                required=True,
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=["symbol"],
                expected_type="list[str]",
            ),
            "save_fields": FieldSchema(
                name="save_fields",
                type=FieldType.ARRAY,
                description="i18n:fields.PostgresNode.save_fields",
                required=True,
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=["symbol", "peak_price", "updated_at"],
                expected_type="list[str]",
            ),
            "aggregations": FieldSchema(
                name="aggregations",
                type=FieldType.OBJECT,
                description="i18n:fields.PostgresNode.aggregations",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"peak_price": "max"},
                expected_type="dict[str, str]",
            ),
            # === SETTINGS: 연결/동기화 설정 ===
            "sync_interval_ms": FieldSchema(
                name="sync_interval_ms",
                type=FieldType.INTEGER,
                description="i18n:fields.PostgresNode.sync_interval_ms",
                default=1000,
                min_value=100,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=1000,
                expected_type="int",
            ),
            "sync_on_change_count": FieldSchema(
                name="sync_on_change_count",
                type=FieldType.INTEGER,
                description="i18n:fields.PostgresNode.sync_on_change_count",
                default=10,
                min_value=1,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=10,
                expected_type="int",
            ),
            "connection_timeout": FieldSchema(
                name="connection_timeout",
                type=FieldType.INTEGER,
                description="i18n:fields.PostgresNode.connection_timeout",
                default=30,
                min_value=5,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=30,
                expected_type="int",
            ),
        }


class HTTPRequestNode(BaseNode):
    """
    HTTP/HTTPS REST API 요청 노드
    
    외부 REST API를 호출하고 응답을 다음 노드에 전달합니다.
    
    Headers 설정:
        UI에서 + 버튼으로 헤더 추가 (Content-Type, Authorization 등)
        headers는 JSON DSL에 노출되지 않습니다.
    
    Example DSL:
        {
            "id": "api_call",
            "type": "HTTPRequestNode",
            "method": "POST",
            "url": "https://api.example.com/data",
            "body": {"name": "test"}
        }
    """

    type: Literal["HTTPRequestNode"] = "HTTPRequestNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.HTTPRequestNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/httprequest.svg"

    # === PARAMETERS: 핵심 HTTP 요청 설정 ===
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        default="GET",
        description="HTTP method",
    )
    url: str = Field(..., description="Request URL ({{ }} 표현식 지원)")
    query_params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body (POST/PUT/PATCH)")

    # === Credential: 인증 정보 참조 ===
    credential_id: Optional[str] = Field(
        default=None, 
        description="Credential ID (credentials 섹션에서 참조)"
    )

    # === Headers: UI에서 동적 추가 ===
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")

    # === SETTINGS: 부가 설정 ===
    timeout_seconds: int = Field(default=30, description="Request timeout (seconds)")
    retry_count: int = Field(default=0, description="Number of retries on failure")
    retry_delay_ms: int = Field(default=1000, description="Delay between retries (ms)")

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
        InputPort(name="data", type="any", description="i18n:ports.http_request_data", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="response", type="any", description="i18n:ports.http_response"),
        OutputPort(name="status_code", type="number", description="i18n:ports.http_status_code"),
        OutputPort(name="success", type="boolean", description="i18n:ports.http_success"),
        OutputPort(name="error", type="string", description="i18n:ports.http_error"),
    ]

    _field_schema: ClassVar[Dict[str, "FieldSchema"]] = {}

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """노드의 설정 가능한 필드 스키마 반환"""
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        
        return {
            # PARAMETERS
            "method": FieldSchema(
                name="method", type=FieldType.ENUM, required=False,
                enum_values=["GET", "POST", "PUT", "PATCH", "DELETE"],
                description="i18n:fields.HTTPRequestNode.method",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="POST",
                expected_type="str",
                ui_component=UIComponent.SELECT,
            ),
            "url": FieldSchema(
                name="url", type=FieldType.STRING, required=True,
                description="i18n:fields.HTTPRequestNode.url",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="https://api.example.com/v1/data",
                example_binding="{{ nodes.config.api_endpoint }}",
                expected_type="str",
                ui_component=UIComponent.TEXT_INPUT,
                placeholder="https://api.example.com/v1/data",
            ),
            "query_params": FieldSchema(
                name="query_params", type=FieldType.KEY_VALUE_PAIRS, required=False,
                description="i18n:fields.HTTPRequestNode.query_params",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example={"symbol": "AAPL", "limit": "100"},
                expected_type="dict[str, str]",
                ui_component=UIComponent.KEY_VALUE_EDITOR,
                object_schema=[
                    {"name": "key", "type": "STRING", "description": "파라미터 이름"},
                    {"name": "value", "type": "STRING", "description": "파라미터 값"},
                ],
            ),
            "body": FieldSchema(
                name="body", type=FieldType.OBJECT, required=False,
                description="i18n:fields.HTTPRequestNode.body",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example={"action": "buy", "symbol": "AAPL", "quantity": 10},
                example_binding="{{ nodes.order.request_body }}",
                expected_type="dict[str, Any]",
                ui_component=UIComponent.TEXTAREA,
                placeholder='{"action": "buy", "symbol": "AAPL", "quantity": 10}',
            ),
            "credential_id": FieldSchema(
                name="credential_id", type=FieldType.CREDENTIAL, required=False,
                description="i18n:fields.HTTPRequestNode.credential_id",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                credential_types=["http_bearer", "http_header", "http_basic", "http_query"],
                ui_component=UIComponent.CREDENTIAL_SELECT,
            ),
            "headers": FieldSchema(
                name="headers", type=FieldType.KEY_VALUE_PAIRS, required=False,
                description="i18n:fields.HTTPRequestNode.headers",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example={"Content-Type": "application/json", "X-Custom-Header": "value"},
                expected_type="dict[str, str]",
                ui_component=UIComponent.KEY_VALUE_EDITOR,
                object_schema=[
                    {"name": "key", "type": "STRING", "description": "헤더 이름"},
                    {"name": "value", "type": "STRING", "description": "헤더 값"},
                ],
                group="advanced",
            ),
            # SETTINGS
            "timeout_seconds": FieldSchema(
                name="timeout_seconds", type=FieldType.INTEGER, required=False,
                default=30,
                description="i18n:fields.HTTPRequestNode.timeout_seconds",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=30,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
                min_value=1,
                max_value=300,
                group="advanced",
            ),
            "retry_count": FieldSchema(
                name="retry_count", type=FieldType.INTEGER, required=False,
                default=0,
                description="i18n:fields.HTTPRequestNode.retry_count",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=3,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
                min_value=0,
                max_value=10,
                group="advanced",
            ),
            "retry_delay_ms": FieldSchema(
                name="retry_delay_ms", type=FieldType.INTEGER, required=False,
                default=1000,
                description="i18n:fields.HTTPRequestNode.retry_delay_ms",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=1000,
                expected_type="int",
                ui_component=UIComponent.NUMBER_INPUT,
                min_value=100,
                max_value=60000,
                group="advanced",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        HTTP 요청 실행
        
        credential_id가 있으면 GenericNodeExecutor에서 credential data가 
        노드 필드로 주입됩니다. credential type에 따라 헤더/쿼리에 적용:
        
        - http_bearer: Authorization: Bearer <token>
        - http_header: <header_name>: <header_value>
        - http_basic: Authorization: Basic <base64(username:password)>
        - http_query: ?<param_name>=<param_value>
        """
        import aiohttp
        import asyncio
        import json
        import base64

        # Credential 데이터 → 헤더/쿼리 적용
        headers = dict(self.headers) if self.headers else {}
        query_params = dict(self.query_params) if self.query_params else {}
        
        # credential에서 주입된 필드들 처리 (GenericNodeExecutor가 주입)
        # http_bearer: token 필드
        if hasattr(self, 'token') and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        # http_header: header_name, header_value 필드
        if hasattr(self, 'header_name') and hasattr(self, 'header_value'):
            if self.header_name and self.header_value:
                headers[self.header_name] = self.header_value
        
        # http_basic: username, password 필드
        if hasattr(self, 'username') and hasattr(self, 'password'):
            if self.username and self.password:
                credentials = f"{self.username}:{self.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
        
        # http_query: param_name, param_value 필드
        if hasattr(self, 'param_name') and hasattr(self, 'param_value'):
            if self.param_name and self.param_value:
                query_params[self.param_name] = self.param_value

        last_error = None
        
        for attempt in range(self.retry_count + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    request_kwargs: Dict[str, Any] = {
                        "method": self.method,
                        "url": self.url,
                        "headers": headers if headers else None,
                        "params": query_params if query_params else None,
                    }

                    # Body 처리 (dict면 JSON 직렬화, 아니면 그대로)
                    if self.body and self.method in ["POST", "PUT", "PATCH"]:
                        if isinstance(self.body, dict):
                            request_kwargs["data"] = json.dumps(self.body)
                            # Content-Type 자동 설정
                            if "Content-Type" not in headers:
                                request_kwargs["headers"] = request_kwargs.get("headers") or {}
                                request_kwargs["headers"]["Content-Type"] = "application/json"
                        else:
                            request_kwargs["data"] = self.body

                    async with session.request(**request_kwargs) as resp:
                        status_code = resp.status

                        # 응답 파싱 (JSON 시도 → 실패하면 text)
                        try:
                            data = await resp.json()
                        except Exception:
                            data = await resp.text()

                        return {
                            "response": data,
                            "status_code": status_code,
                            "success": 200 <= status_code < 300,
                            "error": None,
                        }

            except aiohttp.ClientError as e:
                last_error = f"Network error: {str(e)}"
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
            
            # 재시도 대기
            if attempt < self.retry_count:
                await asyncio.sleep(self.retry_delay_ms / 1000)

        return {
            "response": None,
            "status_code": 0,
            "success": False,
            "error": last_error,
        }


class FieldMappingNode(BaseNode):
    """
    필드명 매핑 노드
    
    데이터의 필드명을 표준 형식으로 변환합니다.
    외부 API, 다양한 데이터 소스의 필드명을 ProgramGarden 표준 형식으로 통일합니다.
    
    주요 용도:
    - 외부 API 응답의 필드명을 표준 OHLCV 형식으로 변환
    - HTTPRequestNode → ConditionNode 사이에서 데이터 정규화
    - AI 에이전트가 description을 참고하여 자동 매핑 제안
    
    지원 데이터 타입:
    - list[dict]: 각 dict의 키 이름 변환
    - dict: dict의 키 이름 변환
    - dict[str, dict]: 중첩 dict의 키 이름 변환
    
    Example DSL:
        {
            "id": "mapper",
            "type": "FieldMappingNode",
            "data": "{{ nodes.api.response.data }}",
            "mappings": [
                {"from": "lastPrice", "to": "close", "description": "마지막 체결가 → 종가"},
                {"from": "vol", "to": "volume", "description": "당일 누적 거래량"}
            ],
            "preserve_unmapped": true
        }
    """

    type: Literal["FieldMappingNode"] = "FieldMappingNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.FieldMappingNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/fieldmapping.svg"

    # 입력 데이터 (바인딩 지원)
    data: Optional[Any] = Field(
        default=None,
        description="Input data to transform (list[dict], dict, or dict[str, dict])",
    )

    # 필드명 매핑 테이블
    mappings: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Field name mapping rules [{from, to, description}, ...]",
        json_schema_extra={
            "ui_component": "field_mapping_editor",
            "help_text": "i18n:fields.FieldMappingNode.mappings",
        },
    )

    # 매핑되지 않은 필드 유지 여부
    preserve_unmapped: bool = Field(
        default=True,
        description="Whether to keep unmapped fields in output",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.data",
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="mapped_data",
            type="any",
            description="i18n:ports.mapped_data",
        ),
        OutputPort(
            name="original_fields",
            type="array",
            description="i18n:ports.original_fields",
        ),
        OutputPort(
            name="mapped_fields",
            type="array",
            description="i18n:ports.mapped_fields",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 입력 데이터 ===
            "data": FieldSchema(
                name="data",
                type=FieldType.OBJECT,  # ANY 대신 OBJECT 사용 (list/dict/nested dict 모두 수용)
                description="i18n:fields.FieldMappingNode.data",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.BINDING_INPUT,
                example=[{"lastPrice": 150, "vol": 1000000}],
                example_binding="{{ nodes.api.response.data }}",
                bindable_sources=["HTTPRequestNode.response"],
                expected_type="list[dict] | dict | dict[str, dict]",
            ),
            # === PARAMETERS: 매핑 테이블 (data의 하위 필드) ===
            "mappings": FieldSchema(
                name="mappings",
                type=FieldType.ARRAY,
                array_item_type=FieldType.OBJECT,
                description="i18n:fields.FieldMappingNode.mappings",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.FIELD_MAPPING_EDITOR,
                child_of="data",  # data 필드 아래 들여쓰기되어 표시
                default=[],
                example=[
                    {"from": "lastPrice", "to": "close"},
                    {"from": "vol", "to": "volume"},
                    {"from": "tradeDate", "to": "date"},
                ],
                expected_type="list[dict]",
                object_schema=[
                    {
                        "name": "from",
                        "type": "STRING",
                        "required": True,
                        "description": "i18n:fields.FieldMappingNode.mappings.from",
                        "placeholder": "원본 필드명 (예: lastPrice)",
                        "ui_width": "50%",
                    },
                    {
                        "name": "to",
                        "type": "STRING",
                        "required": True,
                        "description": "i18n:fields.FieldMappingNode.mappings.to",
                        "placeholder": "표준 필드명 (예: close)",
                        "ui_width": "50%",
                        "suggestions": ["symbol", "exchange", "date", "open", "high", "low", "close", "volume"],
                    },
                ],
                help_text="(+) 버튼으로 매핑 규칙 추가",
            ),
            # === SETTINGS: 부가 설정 ===
            "preserve_unmapped": FieldSchema(
                name="preserve_unmapped",
                type=FieldType.BOOLEAN,
                description="i18n:fields.FieldMappingNode.preserve_unmapped",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.SETTINGS,
                ui_component=UIComponent.CHECKBOX,
                example=True,
                expected_type="bool",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        필드명 매핑 실행
        
        Returns:
            {
                "mapped_data": 변환된 데이터,
                "original_fields": 원본 필드명 목록,
                "mapped_fields": 매핑된 필드명 목록
            }
        """
        data = self.data
        if data is None:
            return {
                "mapped_data": None,
                "original_fields": [],
                "mapped_fields": [],
            }

        # 매핑 딕셔너리 생성 (from -> to)
        mapping_dict = {m["from"]: m["to"] for m in self.mappings if "from" in m and "to" in m}
        
        original_fields: set = set()
        mapped_fields: set = set()

        def transform_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            """단일 dict 변환"""
            result = {}
            for key, value in d.items():
                original_fields.add(key)
                if key in mapping_dict:
                    new_key = mapping_dict[key]
                    mapped_fields.add(new_key)
                    result[new_key] = value
                elif self.preserve_unmapped:
                    result[key] = value
            return result

        # 데이터 타입별 처리
        if isinstance(data, list):
            # list[dict] 처리
            mapped_data = [transform_dict(item) if isinstance(item, dict) else item for item in data]
        elif isinstance(data, dict):
            # dict 또는 dict[str, dict] 처리
            first_value = next(iter(data.values()), None) if data else None
            if isinstance(first_value, dict):
                # dict[str, dict] (중첩 dict)
                mapped_data = {key: transform_dict(val) if isinstance(val, dict) else val for key, val in data.items()}
            else:
                # 일반 dict
                mapped_data = transform_dict(data)
        else:
            # 변환 불가능한 타입은 그대로 반환
            mapped_data = data

        return {
            "mapped_data": mapped_data,
            "original_fields": sorted(list(original_fields)),
            "mapped_fields": sorted(list(mapped_fields)),
        }
