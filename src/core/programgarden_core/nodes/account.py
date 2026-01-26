"""
ProgramGarden Core - Account Nodes

계좌/자산/포지션 관련 노드 (1회성 REST API 조회):
- AccountNode: 계좌 잔고, 보유종목, 미체결 조회

실시간 계좌 정보는 realtime/RealAccountNode 참조
"""

from typing import List, Literal, Dict, TYPE_CHECKING, ClassVar, Optional
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class AccountNode(BaseNode):
    """
    REST API 1회성 계좌 조회 노드

    특정 시점의 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산
    - 미체결 주문

    실시간으로 계속 업데이트가 필요한 경우 RealAccountNode를 사용하세요.
    """

    type: Literal["AccountNode"] = "AccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.AccountNode.description"
    
    # CDN 기반 노드 아이콘 URL
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/account.svg"

    # 설정 가능한 필드 (바인딩 또는 엣지 연결로 설정)
    connection: Optional[Dict] = None  # BrokerNode의 connection 출력
    
    # 상품 유형 선택 (해외주식/해외선물)
    product_type: str = Field(
        default="overseas_stock",
        description="i18n:fields.AccountNode.product_type"
    )

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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """AccountNode의 설정 가능한 필드 스키마."""
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode

        return {
            # === PARAMETERS: 브로커 연결 (필수) ===
            # OBJECT 타입 + EXPRESSION_ONLY → 바인딩 입력 필드 자동 생성
            "connection": FieldSchema(
                name="connection",
                type=FieldType.OBJECT,
                display_name="i18n:fields.AccountNode.connection",
                description="i18n:fields.AccountNode.connection.description",
                required=True,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example={"provider": "ls-sec.co.kr", "product": "overseas_stock", "paper_trading": False},
                example_binding="{{ nodes.broker.connection }}",
                bindable_sources=["BrokerNode.connection"],
                expected_type="broker_connection",
            ),
            # === PARAMETERS: 상품 유형 선택 ===
            # ENUM 타입 → dropdown_button_form_field 자동 생성
            "product_type": FieldSchema(
                name="product_type",
                type=FieldType.ENUM,
                display_name="i18n:fields.AccountNode.product_type",
                description="i18n:fields.AccountNode.product_type.description",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "i18n:enums.product_type.overseas_stock",
                    "overseas_futures": "i18n:enums.product_type.overseas_futures"
                },
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }
