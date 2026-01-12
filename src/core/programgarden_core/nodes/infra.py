"""
ProgramGarden Core - Infra Nodes

Infrastructure/connection nodes:
- StartNode: Workflow entry point
- BrokerNode: Broker connection
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class StartNode(BaseNode):
    """
    Workflow entry point

    Required one per Definition. Starting point of workflow execution.
    """

    type: Literal["StartNode"] = "StartNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.StartNode.description"

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="start", type="signal", description="i18n:ports.start")
    ]


class BrokerNode(BaseNode):
    """
    Broker connection node

    Broker configuration for OpenAPI connection.
    Credentials are provided via credential_id which references stored credentials.
    
    Note:
    - overseas_stock: 모의투자 미지원 (LS증권 제한)
    - overseas_futures: 모의투자 지원
    """

    type: Literal["BrokerNode"] = "BrokerNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.BrokerNode.description"

    # BrokerNode specific config
    provider: str = Field(
        default="ls-sec.co.kr", description="Broker provider (currently only LS Securities supported)"
    )
    product: Literal["overseas_stock", "overseas_futures"] = Field(
        default="overseas_stock", description="Product type"
    )
    credential_id: Optional[str] = Field(
        default=None, description="Reference to stored credentials"
    )
    # paper_trading은 credential에서 관리 (broker_ls.paper_trading)

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        )
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 연결 설정 ===
            "provider": FieldSchema(
                name="provider",
                type=FieldType.STRING,
                description="i18n:fields.BrokerNode.provider",
                default="ls-sec.co.kr",
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.BrokerNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.BrokerNode.credential_id",
                default=None,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            # paper_trading은 credential에서 관리됨 (broker_ls.paper_trading)
        }
