"""
ProgramGarden Core - 노드 베이스 클래스

모든 노드의 기반이 되는 BaseNode와 공통 타입 정의
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal, ClassVar
from pydantic import BaseModel, ConfigDict, Field

from programgarden_core.models.field_binding import FieldSchema, FieldType


class NodeCategory(str, Enum):
    """
    노드 카테고리 (10개 - 금융 도메인 기준)
    
    투자자가 직관적으로 이해할 수 있는 금융 용어 기반 분류
    """

    # 인프라: 워크플로우 시작점, 브로커 연결
    INFRA = "infra"
    
    # 계좌: 잔고, 포지션, 체결 내역 (실시간/REST)
    ACCOUNT = "account"
    
    # 시장: 시세, 종목 목록, 과거 데이터
    MARKET = "market"
    
    # 조건: 매매 조건 판단 (기술적 분석, 로직 조합)
    CONDITION = "condition"
    
    # 주문: 신규/정정/취소 주문, 포지션 사이징
    ORDER = "order"
    
    # 리스크: 리스크 관리, 포트폴리오 배분
    RISK = "risk"
    
    # 스케줄: 시간 기반 트리거, 거래시간 필터
    SCHEDULE = "schedule"
    
    # 데이터: 외부 DB/API 연동 (SQLite, Postgres, HTTP)
    DATA = "data"
    
    # 분석: 백테스트, 차트, 성과 계산
    ANALYSIS = "analysis"
    
    # 시스템: Job 제어, 알림, 서브플로우
    SYSTEM = "system"


class Position(BaseModel):
    """Flutter UI용 노드 위치"""

    x: float = 0.0
    y: float = 0.0


class InputPort(BaseModel):
    """입력 포트 정의"""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    multiple: bool = False  # 여러 엣지 연결 가능 여부
    min_connections: Optional[int] = None  # 최소 연결 수


class OutputPort(BaseModel):
    """출력 포트 정의"""

    name: str
    type: str
    description: Optional[str] = None


class BaseNode(BaseModel):
    """
    모든 노드의 베이스 클래스

    Attributes:
        id: 노드 고유 ID (워크플로우 내에서 유일)
        type: 노드 타입 (클래스명)
        category: 노드 카테고리
        position: Flutter UI용 위치 (선택적)
        config: 노드별 설정
        description: 노드 설명
    """

    id: str = Field(..., description="노드 고유 ID")
    type: str = Field(..., description="노드 타입")
    category: NodeCategory = Field(..., description="노드 카테고리")
    position: Optional[Position] = Field(
        default=None, description="Flutter UI용 노드 위치"
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="노드 설정")
    description: Optional[str] = Field(default=None, description="노드 설명")

    # 메타 정보 (서브클래스에서 오버라이드)
    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = []
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {}
    _img_url: ClassVar[Optional[str]] = None  # 노드 아이콘 이미지 URL

    model_config = ConfigDict(use_enum_values=True, extra="allow")

    def get_inputs(self) -> List[InputPort]:
        """입력 포트 목록 반환"""
        return self._inputs

    def get_outputs(self) -> List[OutputPort]:
        """출력 포트 목록 반환"""
        return self._outputs

    def validate_config(self) -> bool:
        """설정 유효성 검증 (서브클래스에서 오버라이드)"""
        return True

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """
        노드의 설정 가능한 필드 스키마 반환 (UI 렌더링용)
        
        서브클래스에서 오버라이드하여 PARAMETERS/SETTINGS 카테고리 구분.
        
        Returns:
            Dict[str, FieldSchema]: 필드명 → 스키마 매핑
            
        Example:
            @classmethod
            def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
                from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
                return {
                    "url": FieldSchema(name="url", type=FieldType.STRING, 
                        category=FieldCategory.PARAMETERS),
                    "timeout": FieldSchema(name="timeout", type=FieldType.INTEGER,
                        category=FieldCategory.SETTINGS),
                }
        """
        return {}


class PluginNode(BaseNode):
    """
    플러그인을 사용하는 노드의 베이스 클래스

    ConditionNode, NewOrderNode, ModifyOrderNode, CancelOrderNode 등이 상속
    """

    plugin: str = Field(..., description="플러그인 ID (예: RSI, MarketOrder)")
    plugin_version: Optional[str] = Field(
        default=None, description="플러그인 버전 (예: 1.2.0)"
    )
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="플러그인 필드 (고정값, 바인딩, 표현식 지원)",
    )

    def get_plugin_ref(self) -> str:
        """플러그인 참조 문자열 반환 (예: RSI@1.2.0)"""
        if self.plugin_version:
            return f"{self.plugin}@{self.plugin_version}"
        return self.plugin

    def has_expressions(self) -> bool:
        """표현식이 포함된 필드가 있는지 확인"""
        from programgarden_core.models.field_binding import is_expression
        return any(is_expression(v) for v in self.fields.values())


class BaseNotificationNode(BaseNode):
    """
    알림/메시징 노드의 베이스 클래스 (커뮤니티 확장용)
    
    TelegramNode, SlackNode, DiscordNode 등이 상속.
    각 노드는 execute() 메서드를 구현해야 함.
    
    Credential 자동 주입:
        credential_id를 설정하면 GenericNodeExecutor가 실행 전에
        credential 값을 노드 필드에 자동 주입합니다.
        
        Example:
            class TelegramNode(BaseNotificationNode):
                bot_token: Optional[str] = None  # credential에서 자동 주입됨
                chat_id: Optional[str] = None
                
                async def execute(self, context):
                    # self.bot_token에 이미 값이 있음!
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    """
    
    category: NodeCategory = NodeCategory.SYSTEM
    
    # 메시지 템플릿
    template: Optional[str] = Field(
        default=None,
        description="Message template with {{ }} placeholders (e.g., '체결: {{symbol}} {{quantity}}주 @ {{price}}')",
    )
    
    # Credential 연동 (GenericNodeExecutor가 자동 주입)
    credential_id: Optional[str] = Field(
        default=None,
        description="Credential ID from CredentialRegistry. 해당 credential의 필드들이 노드 필드에 자동 주입됨",
    )
    
    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="event_data",
            description="Event data to send notification",
            required=False,
        ),
        InputPort(
            name="trigger",
            type="signal",
            description="Manual trigger signal",
            required=False,
        ),
    ]
    
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="Notification sent confirmation",
        ),
    ]
    
    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        알림 전송 실행 (서브클래스에서 구현 필수)
        
        Args:
            context: ExecutionContext with render_template() etc.
        
        Returns:
            dict with 'sent': bool, and optional 'message_id', 'error' etc.
            
        Note:
            credential_id가 설정되어 있으면 GenericNodeExecutor가 실행 전에
            credential 값을 노드 필드에 자동 주입합니다.
            따라서 self.bot_token, self.api_key 등을 바로 사용할 수 있습니다.
        """
        raise NotImplementedError("Subclass must implement execute()")