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

    # MarketDataNode specific config
    fields: List[str] = Field(
        default=["price", "volume", "ohlcv"],
        description="Fields to query",
    )
    period: Optional[str] = Field(
        default=None, description="Period for OHLCV query (e.g., 1d, 1h, 5m)"
    )
    count: int = Field(default=100, description="Number of data points for OHLCV query")

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
        OutputPort(name="price", type="market_data", description="i18n:ports.price_data"),
        OutputPort(name="volume", type="market_data", description="i18n:ports.volume_data"),
        OutputPort(name="ohlcv", type="ohlcv_data", description="i18n:ports.ohlcv_data"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                description="증권사 연결 정보입니다. BrokerNode(브로커 노드)를 먼저 추가하고, 그 노드의 connection 출력을 여기에 연결하세요.",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
            ),
            # === PARAMETERS: 핵심 조회 설정 ===
            "fields": FieldSchema(
                name="fields",
                type=FieldType.ARRAY,
                description="i18n:fields.MarketDataNode.fields",
                default=["price", "volume", "ohlcv"],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example=["price", "volume", "ohlcv"],
                expected_type="list[str]",
            ),
            "period": FieldSchema(
                name="period",
                type=FieldType.STRING,
                description="i18n:fields.MarketDataNode.period",
                required=False,
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="1d",
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "count": FieldSchema(
                name="count",
                type=FieldType.INTEGER,
                description="i18n:fields.MarketDataNode.count",
                default=100,
                min_value=1,
                max_value=1000,
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=100,
                expected_type="int",
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        
        return {
            # PARAMETERS
            "method": FieldSchema(
                name="method", type=FieldType.ENUM, required=False,
                enum_values=["GET", "POST", "PUT", "PATCH", "DELETE"],
                description="i18n:fields.HTTPRequestNode.method",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example="POST",
                expected_type="str",
            ),
            "url": FieldSchema(
                name="url", type=FieldType.STRING, required=True,
                expression_enabled=True,
                description="i18n:fields.HTTPRequestNode.url",
                category=FieldCategory.PARAMETERS,
                bindable=True,
                example="https://api.example.com/v1/data",
                example_binding="{{ nodes.config.api_endpoint }}",
                expected_type="str",
            ),
            "query_params": FieldSchema(
                name="query_params", type=FieldType.KEY_VALUE_PAIRS, required=False,
                expression_enabled=True,
                description="i18n:fields.HTTPRequestNode.query_params",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"symbol": "AAPL", "limit": "100"},
                expected_type="dict[str, str]",
            ),
            "body": FieldSchema(
                name="body", type=FieldType.OBJECT, required=False,
                expression_enabled=True,
                description="i18n:fields.HTTPRequestNode.body",
                category=FieldCategory.PARAMETERS,
                bindable=True,
                example={"action": "buy", "symbol": "AAPL", "quantity": 10},
                example_binding="{{ nodes.order.request_body }}",
                expected_type="dict[str, Any]",
            ),
            "credential_id": FieldSchema(
                name="credential_id", type=FieldType.CREDENTIAL, required=False,
                description="i18n:fields.HTTPRequestNode.credential_id",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                credential_types=["http_bearer", "http_header", "http_basic", "http_query"],
            ),
            "headers": FieldSchema(
                name="headers", type=FieldType.KEY_VALUE_PAIRS, required=False,
                description="i18n:fields.HTTPRequestNode.headers",
                category=FieldCategory.PARAMETERS,
                bindable=False,
                example={"Content-Type": "application/json", "X-Custom-Header": "value"},
                expected_type="dict[str, str]",
            ),
            # SETTINGS
            "timeout_seconds": FieldSchema(
                name="timeout_seconds", type=FieldType.INTEGER, required=False,
                default=30,
                description="i18n:fields.HTTPRequestNode.timeout_seconds",
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=30,
                expected_type="int",
            ),
            "retry_count": FieldSchema(
                name="retry_count", type=FieldType.INTEGER, required=False,
                default=0,
                description="i18n:fields.HTTPRequestNode.retry_count",
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=3,
                expected_type="int",
            ),
            "retry_delay_ms": FieldSchema(
                name="retry_delay_ms", type=FieldType.INTEGER, required=False,
                default=1000,
                description="i18n:fields.HTTPRequestNode.retry_delay_ms",
                category=FieldCategory.SETTINGS,
                bindable=False,
                example=1000,
                expected_type="int",
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
