"""
ProgramGarden Core - Data Nodes

Data query/storage nodes:
- SQLiteNode: Local SQLite database
- HTTPRequestNode: External REST API request
- FieldMappingNode: Field name mapping

MarketDataNode는 상품별 분리됨:
- data_stock.py → OverseasStockMarketDataNode
- data_futures.py → OverseasFuturesMarketDataNode

계좌 조회는 account_stock/account_futures 참조
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
    RetryableError,
)
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
)


# HTTP 요청 재시도용 커스텀 예외 클래스
class HTTPServerError(Exception):
    """HTTP 5xx 서버 에러 - 재시도 가능"""
    pass


class HTTPRateLimitError(Exception):
    """HTTP 429 Rate Limit 에러 - 재시도 가능"""
    pass


class HTTPNetworkError(Exception):
    """네트워크 연결 에러 - 재시도 가능"""
    pass


class HTTPTimeoutError(Exception):
    """요청 타임아웃 에러 - 재시도 가능"""
    pass


class SQLiteNode(BaseNode):
    """
    로컬 SQLite 데이터베이스 노드 (단순 DB)

    /app/data/ 폴더에 SQLite DB를 생성하고,
    두 가지 모드로 데이터를 조회/저장합니다.
    
    운영 모드:
    - execute_query: 직접 SQL 쿼리 실행 (고급 사용자용)
    - simple: GUI 기반 간단 조작 (select, insert, update, delete, upsert)
    
    주요 용도:
    - 트레일링스탑 High Water Mark (최고점) 추적
    - 전략 상태 저장/복구 (Graceful Restart)
    - 로컬 데이터 캐싱
    
    Example config (simple 모드 - select):
        {
            "db_name": "my_strategy.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "select",
            "columns": ["symbol", "peak_price"],
            "where_clause": "symbol = :symbol"
        }
    
    Example config (execute_query 모드):
        {
            "db_name": "my_strategy.db",
            "operation": "execute_query",
            "query": "SELECT * FROM peak_tracker WHERE symbol = :symbol",
            "parameters": {"symbol": "AAPL"}
        }
    """

    type: Literal["SQLiteNode"] = "SQLiteNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.SQLiteNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/sqlite.svg"

    # === 기본 설정 ===
    db_name: str = Field(
        default="default.db",
        description="데이터베이스 파일명 (/app/data/ 폴더 내)",
    )
    
    # 운영 모드
    operation: Literal["execute_query", "simple"] = Field(
        default="simple",
        description="운영 모드: execute_query(직접 SQL) 또는 simple(GUI 기반)",
    )
    
    # === execute_query 모드 전용 ===
    query: Optional[str] = Field(
        default=None,
        description="실행할 SQL 쿼리 (execute_query 모드)",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="쿼리 파라미터 (SQL 인젝션 방지용 바인딩)",
    )
    
    # === simple 모드 전용 ===
    table: Optional[str] = Field(
        default=None,
        description="테이블 이름 (simple 모드)",
    )
    action: Optional[Literal["select", "insert", "update", "delete", "upsert"]] = Field(
        default="select",
        description="수행할 액션 (simple 모드)",
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="조회/삽입할 컬럼 목록 (select, insert용)",
    )
    where_clause: Optional[str] = Field(
        default=None,
        description="WHERE 조건절 (select, update, delete용). 예: 'symbol = :symbol'",
    )
    values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="삽입/수정할 값 (insert, update, upsert용)",
    )
    on_conflict: Optional[str] = Field(
        default=None,
        description="충돌 시 기준 컬럼 (upsert용). 예: 'symbol'",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
        InputPort(
            name="data",
            type="any",
            description="i18n:ports.sql_input_data",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="rows",
            type="array",
            description="i18n:ports.storage_rows",
        ),
        OutputPort(
            name="affected_count",
            type="integer",
            description="i18n:ports.storage_affected_count",
        ),
        OutputPort(
            name="last_insert_id",
            type="integer",
            description="i18n:ports.sql_last_insert_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent
        return {
            # === PARAMETERS: 기본 설정 ===
            "db_name": FieldSchema(
                name="db_name",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.db_name",
                default="default.db",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CREATABLE_SELECT,
                ui_options={
                    "source": "programgarden_data",
                    "file_extension": ".db",
                    "create_label": "i18n:ui.create_new_database",
                    "deletable": True,
                    "delete_confirm": "i18n:ui.confirm_delete_database",
                },
                example="my_strategy.db",
                expected_type="str",
            ),
            "operation": FieldSchema(
                name="operation",
                type=FieldType.ENUM,
                description="i18n:fields.SQLiteNode.operation",
                default="simple",
                required=True,
                enum_values=["execute_query", "simple"],
                enum_labels={
                    "execute_query": "i18n:enums.sqlite_operation.execute_query",
                    "simple": "i18n:enums.sqlite_operation.simple",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),

            # === execute_query 모드 전용 ===
            "query": FieldSchema(
                name="query",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.query",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CUSTOM_CODE_EDITOR,
                ui_options={"language": "sql"},
                visible_when={"operation": "execute_query"},
                example="SELECT * FROM peak_tracker WHERE symbol = :symbol",
                expected_type="str",
            ),
            "parameters": FieldSchema(
                name="parameters",
                type=FieldType.KEY_VALUE_PAIRS,
                description="i18n:fields.SQLiteNode.parameters",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CUSTOM_KEY_VALUE_EDITOR,
                visible_when={"operation": "execute_query"},
                example={"symbol": "AAPL"},
                expected_type="dict[str, any]",
            ),
            
            # === simple 모드 전용 ===
            "table": FieldSchema(
                name="table",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.table",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CREATABLE_SELECT,
                ui_options={
                    "source_api": "/api/sqlite/{db_name}/tables",
                    "depends_on": "db_name",
                    "create_label": "i18n:ui.create_new_table",
                    "empty_message": "i18n:ui.no_tables_create_first",
                },
                visible_when={"operation": "simple"},
                example="peak_tracker",
                expected_type="str",
            ),
            "action": FieldSchema(
                name="action",
                type=FieldType.ENUM,
                description="i18n:fields.SQLiteNode.action",
                default="select",
                required=False,
                enum_values=["select", "insert", "update", "delete", "upsert"],
                enum_labels={
                    "select": "i18n:enums.sqlite_action.select",
                    "insert": "i18n:enums.sqlite_action.insert",
                    "update": "i18n:enums.sqlite_action.update",
                    "delete": "i18n:enums.sqlite_action.delete",
                    "upsert": "i18n:enums.sqlite_action.upsert",
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                visible_when={"operation": "simple"},
            ),
            "columns": FieldSchema(
                name="columns",
                type=FieldType.ARRAY,
                description="i18n:fields.SQLiteNode.columns",
                required=False,
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_options={
                    "multiple": True,
                    "source_api": "/api/sqlite/{db_name}/tables/{table}/columns",
                    "depends_on": ["db_name", "table"],
                    "empty_message": "i18n:ui.select_table_first",
                },
                visible_when={"operation": "simple", "action": ["select", "insert"]},
                example=["symbol", "peak_price", "updated_at"],
                expected_type="list[str]",
                help_text="i18n:fields.SQLiteNode.columns_help",
            ),
            "where_clause": FieldSchema(
                name="where_clause",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.where_clause_detailed",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                visible_when={"operation": "simple", "action": ["select", "update", "delete"]},
                example="symbol = :symbol",
                expected_type="str",
            ),
            "values": FieldSchema(
                name="values",
                type=FieldType.KEY_VALUE_PAIRS,
                description="i18n:fields.SQLiteNode.values",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CUSTOM_KEY_VALUE_EDITOR,
                visible_when={"operation": "simple", "action": ["insert", "update", "upsert"]},
                example={"symbol": "AAPL", "peak_price": 195.50},
                expected_type="dict[str, any]",
            ),
            "on_conflict": FieldSchema(
                name="on_conflict",
                type=FieldType.STRING,
                description="i18n:fields.SQLiteNode.on_conflict",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                visible_when={"operation": "simple", "action": "upsert"},
                example="symbol",
                expected_type="str",
                help_text="i18n:fields.SQLiteNode.on_conflict_help",
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
    retry_count: int = Field(default=0, description="Number of retries on failure (legacy)")
    retry_delay_ms: int = Field(default=1000, description="Delay between retries (ms) (legacy)")

    # === Resilience: 재시도/실패 처리 ===
    resilience: ResilienceConfig = Field(
        default_factory=ResilienceConfig,
        description="재시도 및 실패 처리 설정",
    )

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
            ),
            "url": FieldSchema(
                name="url", type=FieldType.STRING, required=True,
                description="i18n:fields.HTTPRequestNode.url",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="https://api.example.com/v1/data",
                example_binding="{{ nodes.config.api_endpoint }}",
                expected_type="str",
                placeholder="https://api.example.com/v1/data",
            ),
            "query_params": FieldSchema(
                name="query_params", type=FieldType.KEY_VALUE_PAIRS, required=False,
                description="i18n:fields.HTTPRequestNode.query_params",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example={"symbol": "AAPL", "limit": "100"},
                expected_type="dict[str, str]",
                ui_component=UIComponent.CUSTOM_KEY_VALUE_EDITOR,
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
                ui_options={"maxLines": 5},
                placeholder='{"action": "buy", "symbol": "AAPL", "quantity": 10}',
            ),
            "credential_id": FieldSchema(
                name="credential_id", type=FieldType.CREDENTIAL, required=False,
                description="i18n:fields.HTTPRequestNode.credential_id",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                credential_types=["http_bearer", "http_header", "http_basic", "http_query"],
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
            ),
            "headers": FieldSchema(
                name="headers", type=FieldType.KEY_VALUE_PAIRS, required=False,
                description="i18n:fields.HTTPRequestNode.headers",
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example={"Content-Type": "application/json", "X-Custom-Header": "value"},
                expected_type="dict[str, str]",
                ui_component=UIComponent.CUSTOM_KEY_VALUE_EDITOR,
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

        재시도 동작:
        - resilience.retry.enabled=True 설정 시 RetryExecutor가 자동 재시도
        - 5xx 서버 에러, 네트워크 에러, 타임아웃 → Exception raise → 재시도
        - 4xx 클라이언트 에러 → 재시도 불가, 결과 반환
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

                    # 5xx 서버 에러 → Exception raise (RetryExecutor가 재시도)
                    if status_code >= 500:
                        error_msg = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)[:200]
                        raise HTTPServerError(f"HTTP {status_code}: {error_msg}")

                    # 429 Rate Limit → Exception raise (RetryExecutor가 재시도)
                    if status_code == 429:
                        raise HTTPRateLimitError(f"HTTP 429: Rate limit exceeded")

                    # 4xx 클라이언트 에러 → 재시도 불가, 결과 반환
                    if status_code >= 400:
                        return {
                            "response": data,
                            "status_code": status_code,
                            "success": False,
                            "error": f"HTTP {status_code}",
                        }

                    # 성공 (2xx, 3xx)
                    return {
                        "response": data,
                        "status_code": status_code,
                        "success": True,
                        "error": None,
                    }

        except aiohttp.ClientError as e:
            # 네트워크 에러 → RetryExecutor가 재시도
            raise HTTPNetworkError(f"Network error: {e}")
        except asyncio.TimeoutError as e:
            # 타임아웃 → RetryExecutor가 재시도
            raise HTTPTimeoutError(f"Request timeout after {self.timeout_seconds}s")

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        """
        HTTP 에러가 재시도 가능한지 판단.

        Args:
            error: 발생한 예외

        Returns:
            RetryableError 유형, 또는 None (재시도 불가)
        """
        error_str = str(error).lower()

        # 타임아웃
        if "timeout" in error_str or "timed out" in error_str:
            return RetryableError.TIMEOUT

        # Rate limit (429)
        if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return RetryableError.RATE_LIMIT

        # 네트워크 에러
        if "connection" in error_str or "network" in error_str or "unreachable" in error_str:
            return RetryableError.NETWORK_ERROR

        # 서버 에러 (5xx)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return RetryableError.SERVER_ERROR

        return None


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
                ui_component=UIComponent.CUSTOM_FIELD_MAPPING_EDITOR,
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
