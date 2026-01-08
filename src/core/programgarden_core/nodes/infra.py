"""
ProgramGarden Core - Infra Nodes

Infrastructure/connection nodes:
- StartNode: Workflow entry point
- BrokerNode: Broker connection
"""

from typing import Optional, List, Literal, Dict, ClassVar
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.models.field_binding import FieldSchema, FieldType


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
    paper_trading: bool = Field(
        default=False, description="Use paper trading (overseas_futures only)"
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
        )
    ]
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {
        "provider": FieldSchema(
            name="provider",
            type=FieldType.STRING,
            description="Broker provider",
            default="ls-sec.co.kr",
            bindable=False,
        ),
        "product": FieldSchema(
            name="product",
            type=FieldType.ENUM,
            description="Product type (overseas_stock/overseas_futures)",
            default="overseas_stock",
            enum_values=["overseas_stock", "overseas_futures"],
            bindable=False,
        ),
        "credential_id": FieldSchema(
            name="credential_id",
            type=FieldType.STRING,
            description="Select stored credentials",
            default=None,
            bindable=False,
        ),
        "paper_trading": FieldSchema(
            name="paper_trading",
            type=FieldType.BOOLEAN,
            description="Use paper trading (overseas_futures only, overseas_stock not supported)",
            default=False,
            bindable=False,
            # UI 힌트: overseas_stock 선택 시 비활성화
            extra={"ui_hint": {"disable_when": {"product": "overseas_stock"}}},
        ),
    }
