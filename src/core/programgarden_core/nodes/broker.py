"""
ProgramGarden Core - Broker Nodes

상품별 브로커 연결 노드:
- StockBrokerNode: 해외주식 전용 브로커
- FuturesBrokerNode: 해외선물 전용 브로커
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING, ClassVar
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
)


class BaseBrokerNode(BaseNode):
    """
    브로커 노드 공통 베이스 클래스

    모든 브로커 노드의 공통 속성:
    - provider: 증권사 (현재 LS증권만 지원)
    - credential_id: 인증정보 참조
    - connection 출력 포트
    """

    category: NodeCategory = NodeCategory.INFRA

    provider: str = Field(
        default="ls-sec.co.kr", description="Broker provider"
    )
    credential_id: Optional[str] = Field(
        default=None, description="Reference to stored credentials"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        )
    ]


class StockBrokerNode(BaseBrokerNode):
    """
    해외주식 전용 브로커 연결 노드

    LS증권 OpenAPI를 통해 해외주식 거래를 위한 브로커 연결을 생성합니다.

    Note:
    - 해외주식은 모의투자 미지원 (LS증권 제한)
    - credential_types: broker_ls_stock
    """

    type: Literal["StockBrokerNode"] = "StockBrokerNode"
    description: str = "i18n:nodes.StockBrokerNode.description"

    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/broker_stock.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode,
        )
        return {
            "provider": FieldSchema(
                name="provider",
                type=FieldType.ENUM,
                description="i18n:fields.StockBrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "LS증권"},
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.StockBrokerNode.credential_id",
                default=None,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CREDENTIAL_SELECT,
                credential_types=["broker_ls_stock"],
            ),
        }


class FuturesBrokerNode(BaseBrokerNode):
    """
    해외선물 전용 브로커 연결 노드

    LS증권 OpenAPI를 통해 해외선물 거래를 위한 브로커 연결을 생성합니다.

    Note:
    - 해외선물은 모의투자 지원
    - credential_types: broker_ls_futures
    """

    type: Literal["FuturesBrokerNode"] = "FuturesBrokerNode"
    description: str = "i18n:nodes.FuturesBrokerNode.description"

    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/broker_futures.svg"
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode,
        )
        return {
            "provider": FieldSchema(
                name="provider",
                type=FieldType.ENUM,
                description="i18n:fields.FuturesBrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "LS증권"},
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.SELECT,
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.FuturesBrokerNode.credential_id",
                default=None,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CREDENTIAL_SELECT,
                credential_types=["broker_ls_futures"],
            ),
        }
