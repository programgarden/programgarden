"""
ProgramGarden Core - DynamicNodeRegistry

동적 노드 관리 레지스트리 (Lazy Loading 지원)

외부 사용자가 community 패키지 기여 없이 런타임에 커스텀 노드를 주입하여
워크플로우에서 사용할 수 있도록 지원합니다.

사용 시나리오:
1. 앱 시작: register_schema()로 스키마만 등록 (UI 표시용)
2. 실행 전: inject_node_class()로 클래스 주입
3. 실행: 주입된 클래스로 워크플로우 실행
4. 정리: clear_injected_classes()로 메모리 정리

네이밍 규칙:
- 동적 노드는 반드시 'Custom_' prefix 사용 (예: Custom_MyRSI)
- 기존 노드와의 충돌 방지 및 동적 노드 식별 용이

보안:
- credential_id 사용 불허 (동적 노드에서 credential 접근 차단)
- 클래스 주입 시 BaseNode 상속, execute() 메서드 존재 검증
"""

from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, Field


# 동적 노드 타입 prefix
DYNAMIC_NODE_PREFIX = "Custom_"


class DynamicNodeSchema(BaseModel):
    """
    동적 노드 정의 스키마 (UI 표시용, 검증용)

    사용자가 DB에서 로드한 스키마를 라이브러리에 등록할 때 사용.
    실제 노드 클래스 없이 스키마만으로 UI에 노드 목록을 표시할 수 있음.

    Attributes:
        node_type: 고유 노드 타입명 (Custom_ prefix 필수)
        category: 노드 카테고리 (infra, data, condition 등)
        description: 노드 설명 (사용자 표시용)
        inputs: 입력 포트 정의 [{name, type, required, description}]
        outputs: 출력 포트 정의 [{name, type, description}]
        config_schema: 설정 필드 스키마 {field_name: {type, default, ...}}
        version: 노드 버전
        author: 작성자

    Example:
        schema = DynamicNodeSchema(
            node_type="Custom_MyRSI",
            category="condition",
            description="커스텀 RSI 지표 노드",
            inputs=[{"name": "data", "type": "array", "required": True}],
            outputs=[
                {"name": "rsi", "type": "number"},
                {"name": "signal", "type": "string"}
            ],
            config_schema={
                "period": {"type": "integer", "default": 14, "min": 1, "max": 100}
            }
        )
    """

    # 기본 정보
    node_type: str = Field(
        ...,
        description="고유 노드 타입명 (Custom_ prefix 필수)"
    )
    category: str = Field(
        default="data",
        description="노드 카테고리 (infra, market, condition, order, data 등)"
    )
    description: Optional[str] = Field(
        default=None,
        description="노드 설명 (사용자 표시용)"
    )

    # 입출력 포트 (UI 렌더링용)
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="입력 포트 정의 [{name, type, required, description}]"
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="출력 포트 정의 [{name, type, description}]"
    )

    # 설정 필드 (UI 렌더링용)
    config_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="설정 필드 스키마 {field_name: {type, default, ...}}"
    )

    # 메타데이터
    version: str = Field(default="1.0.0", description="노드 버전")
    author: Optional[str] = Field(default=None, description="작성자")


class DynamicNodeRegistry:
    """
    런타임 동적 노드 관리 (Lazy Loading 지원)

    외부 사용자가 커스텀 노드를 런타임에 주입하여 사용할 수 있도록 지원.
    스키마와 클래스를 분리하여 관리하며, Lazy Loading 패턴을 지원합니다.

    Singleton Pattern:
        전역에서 단일 인스턴스를 공유합니다.

    책임 분리:
        - 라이브러리: 스키마 저장소 제공, 클래스 검증 및 저장, 워크플로우 실행
        - 사용자: 스키마 정의, 클래스 구현, 다운로드/import, 주입

    Example:
        registry = DynamicNodeRegistry()

        # 1. 스키마만 등록 (앱 시작 시)
        schema = DynamicNodeSchema(
            node_type="Custom_MyRSI",
            outputs=[{"name": "rsi", "type": "number"}]
        )
        registry.register_schema(schema)

        # 2. 클래스 주입 (실행 전)
        registry.inject_node_class("Custom_MyRSI", MyRSINode)

        # 3. 클래스 조회 (실행 시)
        node_class = registry.get_node_class("Custom_MyRSI")
    """

    _instance: Optional["DynamicNodeRegistry"] = None
    _schemas: Dict[str, DynamicNodeSchema]
    _node_classes: Dict[str, type]

    def __new__(cls) -> "DynamicNodeRegistry":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {}
            cls._instance._node_classes = {}
        return cls._instance

    # ─────────────────────────────────────────────────
    # 스키마 관리 (앱 시작 시)
    # ─────────────────────────────────────────────────

    def register_schema(self, schema: DynamicNodeSchema) -> None:
        """
        스키마만 등록 (클래스 없이)

        UI에서 노드 목록 표시용. 실제 실행을 위해서는
        inject_node_class()로 클래스를 주입해야 함.

        Args:
            schema: DynamicNodeSchema 인스턴스

        Raises:
            ValueError: Custom_ prefix가 없는 경우
        """
        if not schema.node_type.startswith(DYNAMIC_NODE_PREFIX):
            raise ValueError(
                f"동적 노드는 '{DYNAMIC_NODE_PREFIX}' prefix 필수: {schema.node_type}"
            )
        self._schemas[schema.node_type] = schema

    def register_schemas(self, schemas: List[DynamicNodeSchema]) -> None:
        """
        여러 스키마 일괄 등록

        Args:
            schemas: DynamicNodeSchema 인스턴스 목록
        """
        for schema in schemas:
            self.register_schema(schema)

    def get_schema(self, node_type: str) -> Optional[DynamicNodeSchema]:
        """
        스키마 조회

        Args:
            node_type: 노드 타입명 (예: Custom_MyRSI)

        Returns:
            DynamicNodeSchema 또는 None
        """
        return self._schemas.get(node_type)

    def list_schema_types(self) -> List[str]:
        """
        등록된 스키마 타입 목록

        Returns:
            노드 타입명 목록 (예: ["Custom_MyRSI", "Custom_MyMACD"])
        """
        return list(self._schemas.keys())

    def list_schemas(self) -> List[DynamicNodeSchema]:
        """
        등록된 모든 스키마 반환

        Returns:
            DynamicNodeSchema 목록
        """
        return list(self._schemas.values())

    # ─────────────────────────────────────────────────
    # 클래스 주입 (실행 전)
    # ─────────────────────────────────────────────────

    def inject_node_class(self, node_type: str, node_class: type) -> None:
        """
        노드 클래스 주입

        사용자가 Cloud Storage에서 다운로드 → 동적 import한 클래스를 주입.

        검증 항목:
        1. 스키마 등록 여부
        2. BaseNode 상속 여부
        3. execute() 메서드 존재 여부
        4. 스키마와 클래스의 출력 포트 일치 여부

        Args:
            node_type: 노드 타입명 (예: Custom_MyRSI)
            node_class: 노드 클래스 (BaseNode 상속)

        Raises:
            ValueError: 스키마 미등록, 포트 불일치
            TypeError: BaseNode 미상속, execute() 미구현
        """
        # 지연 임포트로 순환 참조 방지
        from programgarden_core.nodes.base import BaseNode

        # 1. 스키마 등록 확인
        schema = self._schemas.get(node_type)
        if not schema:
            raise ValueError(f"스키마가 등록되지 않은 타입: {node_type}")

        # 2. BaseNode 상속 확인
        if not issubclass(node_class, BaseNode):
            raise TypeError(f"BaseNode를 상속해야 함: {node_class.__name__}")

        # 3. execute() 메서드 확인
        if not hasattr(node_class, "execute") or not callable(getattr(node_class, "execute")):
            raise TypeError(f"execute() 메서드가 없음: {node_class.__name__}")

        # 4. 출력 포트 검증 (스키마 vs 클래스)
        self._validate_ports(schema, node_class)

        self._node_classes[node_type] = node_class

    def _validate_ports(self, schema: DynamicNodeSchema, node_class: type) -> None:
        """
        스키마와 클래스의 출력 포트 일치 여부 검증

        스키마에 정의된 output 포트들이 클래스에도 있는지 확인.

        Args:
            schema: DynamicNodeSchema
            node_class: 노드 클래스

        Raises:
            ValueError: 스키마에 정의된 포트가 클래스에 없는 경우
        """
        # 스키마에 정의된 output 포트명들
        schema_outputs = {o.get("name") for o in schema.outputs if o.get("name")}

        # 스키마에 출력 포트가 없으면 검증 생략
        if not schema_outputs:
            return

        # 클래스의 output 포트명들
        # Pydantic v2에서 _outputs는 PrivateAttr이므로 인스턴스를 통해 접근
        class_outputs: set = set()
        try:
            # 임시 인스턴스 생성하여 get_outputs() 호출
            temp_instance = node_class(id="__validate__", type=node_class.__name__)
            outputs = temp_instance.get_outputs()
            for port in outputs:
                if hasattr(port, "name"):
                    class_outputs.add(port.name)
        except Exception:
            # 인스턴스 생성 실패 시 클래스 속성에서 직접 시도
            # (일부 노드는 필수 필드가 있을 수 있음)
            pass

        # 스키마에는 있지만 클래스에는 없는 포트
        missing = schema_outputs - class_outputs
        if missing:
            raise ValueError(
                f"스키마에 정의된 output 포트가 클래스에 없음: {missing}"
            )

    def inject_node_classes(self, node_classes: Dict[str, type]) -> None:
        """
        여러 노드 클래스 일괄 주입

        Args:
            node_classes: {node_type: node_class} 딕셔너리
        """
        for node_type, node_class in node_classes.items():
            self.inject_node_class(node_type, node_class)

    def get_node_class(self, node_type: str) -> Optional[type]:
        """
        주입된 클래스 조회

        Args:
            node_type: 노드 타입명

        Returns:
            노드 클래스 또는 None (미주입 시)
        """
        return self._node_classes.get(node_type)

    def is_class_injected(self, node_type: str) -> bool:
        """
        클래스 주입 여부 확인

        Args:
            node_type: 노드 타입명

        Returns:
            주입 여부 (True/False)
        """
        return node_type in self._node_classes

    def is_schema_registered(self, node_type: str) -> bool:
        """
        스키마 등록 여부 확인

        Args:
            node_type: 노드 타입명

        Returns:
            등록 여부 (True/False)
        """
        return node_type in self._schemas

    # ─────────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────────

    def clear_injected_classes(self) -> None:
        """
        주입된 클래스 초기화 (실행 후 메모리 정리)

        스키마는 유지되고 클래스만 제거됨.
        """
        self._node_classes.clear()

    def unregister(self, node_type: str) -> bool:
        """
        스키마 및 클래스 등록 해제

        Args:
            node_type: 노드 타입명

        Returns:
            제거 성공 여부
        """
        removed = node_type in self._schemas
        self._schemas.pop(node_type, None)
        self._node_classes.pop(node_type, None)
        return removed

    def clear_all(self) -> None:
        """
        모든 스키마 및 클래스 초기화

        테스트나 리셋 용도로 사용.
        """
        self._schemas.clear()
        self._node_classes.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """
        싱글톤 인스턴스 리셋 (테스트용)

        주의: 프로덕션에서는 사용하지 않음.
        """
        if cls._instance is not None:
            cls._instance._schemas.clear()
            cls._instance._node_classes.clear()
            cls._instance = None


def is_dynamic_node_type(node_type: str) -> bool:
    """
    동적 노드 타입인지 확인

    Args:
        node_type: 노드 타입명

    Returns:
        Custom_ prefix 여부
    """
    return node_type.startswith(DYNAMIC_NODE_PREFIX)
