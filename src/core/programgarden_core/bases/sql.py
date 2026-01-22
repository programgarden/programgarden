"""
ProgramGarden Core - SQL Base Classes

SQL 데이터베이스 노드를 위한 베이스 클래스:
- BaseSQLNode: SQL 데이터베이스 공통 기능 (SQLite, PostgreSQL 등)

계층 구조:
    BaseStorageNode
        │
        └── BaseSQLNode (이 파일)
                ├── SQLiteNode
                └── PostgresNode
"""

from typing import List, Optional, Literal, TYPE_CHECKING

from pydantic import Field

from programgarden_core.bases.storage import BaseStorageNode
from programgarden_core.nodes.base import InputPort, OutputPort

if TYPE_CHECKING:
    pass


class BaseSQLNode(BaseStorageNode):
    """
    SQL 데이터베이스 노드의 공통 베이스 클래스
    
    두 가지 운영 모드 지원:
    - execute_query: 직접 SQL 쿼리 실행
    - simple: GUI 기반 간단 조작 (select, insert, update, delete, upsert)
    
    공통 기능:
    - 쿼리 실행 인터페이스
    - 파라미터 바인딩 (SQL 인젝션 방지)
    - 트랜잭션 관리
    """
    
    # 운영 모드 (공통)
    operation: Literal["execute_query", "simple"] = Field(
        default="simple",
        description="운영 모드: execute_query(직접 SQL) 또는 simple(GUI 기반)",
    )
    
    # execute_query 모드 전용 필드
    query: Optional[str] = Field(
        default=None,
        description="실행할 SQL 쿼리 (execute_query 모드)",
    )
    parameters: Optional[dict] = Field(
        default=None,
        description="쿼리 파라미터 (execute_query 모드)",
    )
    
    # simple 모드 전용 필드
    table: Optional[str] = Field(
        default=None,
        description="테이블 이름 (simple 모드)",
    )
    action: Optional[Literal["select", "insert", "update", "delete", "upsert"]] = Field(
        default=None,
        description="수행할 액션 (simple 모드)",
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="조회/삽입할 컬럼 목록 (select, insert용)",
    )
    where_clause: Optional[str] = Field(
        default=None,
        description="WHERE 조건절 (select, update, delete용)",
    )
    values: Optional[dict] = Field(
        default=None,
        description="삽입/수정할 값 (insert, update, upsert용)",
    )
    on_conflict: Optional[str] = Field(
        default=None,
        description="충돌 시 기준 컬럼 (upsert용)",
    )
    
    # 입력 포트 - 동적 데이터 바인딩
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
    
    # 출력 포트
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
