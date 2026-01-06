"""
ProgramGarden Core - Data Nodes

Data query nodes (REST API one-time):
- MarketDataNode: REST API market data query
- AccountNode: REST API account query
"""

from typing import Optional, List, Literal
from pydantic import Field

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
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.MarketDataNode.description"

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


class AccountNode(BaseNode):
    """
    REST API one-time account query node

    Fetches account information at a specific point in time via REST API
    """

    type: Literal["AccountNode"] = "AccountNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.AccountNode.description"

    _inputs: List[InputPort] = [
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
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
            name="held_symbols", type="symbol_list", description="i18n:ports.held_symbols"
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
        ),
        OutputPort(
            name="open_orders", type="order_list", description="i18n:ports.open_orders"
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
        ),
    ]


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


class PostgresNode(BaseNode):
    """
    외부 PostgreSQL 데이터베이스 노드

    외부 PostgreSQL DB에 데이터를 저장/조회합니다.
    연결 정보는 secrets 네임스페이스를 통해 참조합니다.
    
    주요 용도:
    - 분산 환경에서 상태 공유
    - 대용량 데이터 저장
    - 백테스트 결과 저장
    
    Example config:
        {
            "connection": {
                "host": "{{ secrets.mydb.host }}",
                "port": "{{ secrets.mydb.port }}",
                "database": "{{ secrets.mydb.database }}",
                "username": "{{ secrets.mydb.username }}",
                "password": "{{ secrets.mydb.password }}"
            },
            "table": "trailing_stop_state",
            "key_fields": ["symbol"],
            "save_fields": ["symbol", "peak_price", "peak_pnl_rate", "updated_at"],
            "aggregations": {"peak_price": "max", "peak_pnl_rate": "max"}
        }
    """

    type: Literal["PostgresNode"] = "PostgresNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.PostgresNode.description"

    # 연결 정보 (secrets 네임스페이스 참조)
    connection: dict = Field(
        ...,
        description="DB 연결 정보 ({{ secrets.xxx }} 형태로 참조)",
    )

    # 테이블 설정
    table: str = Field(..., description="테이블 이름")
    schema_name: str = Field(
        default="public",
        description="스키마 이름",
    )
    key_fields: List[str] = Field(
        ...,
        description="Primary Key 필드 목록",
    )
    save_fields: List[str] = Field(
        ...,
        description="저장할 필드 목록",
    )

    # 집계 설정
    aggregations: Optional[dict] = Field(
        default=None,
        description="필드별 집계 함수 (예: {'peak_price': 'max'})",
    )

    # 동기화 설정
    sync_interval_ms: int = Field(
        default=1000,
        description="DB 동기화 주기 (밀리초)",
    )
    sync_on_change_count: int = Field(
        default=10,
        description="변경 횟수 기준 동기화",
    )

    # 추가 옵션
    ssl_enabled: bool = Field(
        default=False,
        description="SSL 연결 사용 여부",
    )
    connection_timeout: int = Field(
        default=30,
        description="연결 타임아웃 (초)",
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
        OutputPort(
            name="query_result",
            type="any",
            description="i18n:ports.query_result",
        ),
    ]
