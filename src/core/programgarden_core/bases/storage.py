"""
ProgramGarden Core - Storage Base Classes

데이터 저장소 노드를 위한 베이스 클래스:
- BaseStorageNode: 모든 스토리지 노드의 최상위 클래스

계층 구조:
    BaseStorageNode (최상위, 모든 스토리지)
        │
        ├── BaseSQLNode (SQL 공통) - sql.py
        │       └── SQLiteNode
        │
        └── BaseNoSQLNode (향후)
                ├── MongoNode
                └── RedisNode
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from programgarden_core.nodes.base import BaseNode, InputPort, OutputPort

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema


class BaseStorageNode(BaseNode):
    """
    모든 스토리지 노드의 최상위 베이스 클래스
    
    공통 기능:
    - 연결 관리 (connect, disconnect)
    - 기본 입출력 포트 정의
    - 스토리지 상태 추적
    """
    
    # 공통 입력 포트
    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            required=False,
        ),
    ]
    
    # 공통 출력 포트
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
    ]
    
    @classmethod
    @abstractmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """필드 스키마 반환 - 하위 클래스에서 구현"""
        raise NotImplementedError
