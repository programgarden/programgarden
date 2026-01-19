"""
ProgramGarden Core - Infra Nodes

Infrastructure/connection nodes:
- StartNode: Workflow entry point
- BrokerNode: Broker connection
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
)


class StartNode(BaseNode):
    """
    Workflow entry point

    Required one per Definition. Starting point of workflow execution.
    """

    type: Literal["StartNode"] = "StartNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.StartNode.description"
    
    # CDN 기반 노드 아이콘 URL (TODO: 실제 CDN URL로 교체)
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/start.svg"

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="start", type="signal", description="i18n:ports.start")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """StartNode has no configurable fields."""
        return {}


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
    
    # CDN 기반 노드 아이콘 URL (TODO: 실제 CDN URL로 교체)
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/broker.svg"

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
                type=FieldType.ENUM,
                description="i18n:fields.BrokerNode.provider",
                default="ls-sec.co.kr",
                enum_values=["ls-sec.co.kr"],
                enum_labels={"ls-sec.co.kr": "LS증권"},
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="select",
                example="ls-sec.co.kr",
                expected_type="str",
            ),
            "product": FieldSchema(
                name="product",
                type=FieldType.ENUM,
                description="i18n:fields.BrokerNode.product",
                default="overseas_stock",
                enum_values=["overseas_stock", "overseas_futures"],
                enum_labels={
                    "overseas_stock": "i18n:enums.product.overseas_stock",
                    "overseas_futures": "i18n:enums.product.overseas_futures"
                },
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="select",
                example="overseas_stock",
                expected_type="str",
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.BrokerNode.credential_id",
                default=None,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="select:credential",
                credential_types=["broker_ls"],
                example="my-broker-cred",
                expected_type="str",
            ),
            # paper_trading은 credential에서 관리됨 (broker_ls.paper_trading)
        }


class ThrottleNode(BaseNode):
    """
    Data flow control node (Throttle)
    
    Controls the frequency of data flow from realtime nodes to prevent
    excessive execution of downstream nodes and API rate limiting.
    
    Modes:
    - skip: Ignore incoming data during cooldown
    - latest: Keep only the latest data during cooldown, execute when cooldown ends
    """
    
    type: Literal["ThrottleNode"] = "ThrottleNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.ThrottleNode.description"
    
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/throttle.svg"
    
    # ThrottleNode specific config
    mode: Literal["skip", "latest"] = Field(
        default="latest",
        description="Cooldown mode: skip (ignore) or latest (keep newest)"
    )
    interval_sec: float = Field(
        default=5.0,
        ge=0.1,
        le=300.0,
        description="Minimum execution interval in seconds"
    )
    pass_first: bool = Field(
        default=True,
        description="Pass first data immediately without waiting"
    )
    
    _inputs: List[InputPort] = [
        InputPort(name="data", type="any", description="i18n:ports.data")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="data", type="any", description="i18n:ports.data"),
        OutputPort(name="_throttle_stats", type="object", description="i18n:ports.throttle_stats"),
    ]
    
    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="i18n:fields.ThrottleNode.mode",
                default="latest",
                enum_values=["skip", "latest"],
                enum_labels={
                    "skip": "i18n:enums.throttle_mode.skip",
                    "latest": "i18n:enums.throttle_mode.latest"
                },
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="select",
                example="latest",
                expected_type="str",
            ),
            "interval_sec": FieldSchema(
                name="interval_sec",
                type=FieldType.NUMBER,
                description="i18n:fields.ThrottleNode.interval_sec",
                default=5.0,
                min_value=0.1,
                max_value=300.0,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="number_input",
                placeholder="5.0",
                example=5.0,
                expected_type="float",
            ),
            "pass_first": FieldSchema(
                name="pass_first",
                type=FieldType.BOOLEAN,
                description="i18n:fields.ThrottleNode.pass_first",
                default=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="checkbox",
                example=True,
                expected_type="bool",
            ),
        }
