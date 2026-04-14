"""
ProgramGarden Core - Infra Nodes

Infrastructure nodes:
- StartNode: Workflow entry point
- ThrottleNode: Data flow control
- SplitNode: Split list into individual items (item-based execution)
- AggregateNode: Aggregate individual items into a list
- IfNode: Conditional branching (if/else)
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING, ClassVar, Any
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
    _img_url: ClassVar[str] = ""

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="start", type="signal", description="i18n:ports.start")
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """StartNode has no configurable fields."""
        return {}


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
    
    _img_url: ClassVar[str] = ""
    
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
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
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
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
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="5.0",
                example=5.0,
                expected_type="float",
            ),
            "pass_first": FieldSchema(
                name="pass_first",
                type=FieldType.BOOLEAN,
                description="i18n:fields.ThrottleNode.pass_first",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=True,
                expected_type="bool",
            ),
        }


class SplitNode(BaseNode):
    """
    Split list into individual items (item-based execution)

    Converts a list input into individual items, triggering downstream nodes
    once for each item. Works with AggregateNode to collect results.

    Execution modes:
    - Sequential (default): Execute items one by one with optional delay
    - Parallel: Execute all items concurrently (relies on internal throttling)
    """

    type: Literal["SplitNode"] = "SplitNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.SplitNode.description"

    _img_url: ClassVar[str] = ""

    # SplitNode specific config
    parallel: bool = Field(
        default=False,
        description="Execute all items in parallel (default: sequential)"
    )
    delay_ms: int = Field(
        default=0,
        ge=0,
        le=60000,
        description="Delay between items in milliseconds (sequential mode only)"
    )
    continue_on_error: bool = Field(
        default=True,
        description="Continue execution even if one item fails"
    )

    _inputs: List[InputPort] = [
        InputPort(name="array", type="array", description="i18n:ports.split_array")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="item", type="any", description="i18n:ports.split_item"),
        OutputPort(name="index", type="integer", description="i18n:ports.split_index"),
        OutputPort(name="total", type="integer", description="i18n:ports.split_total"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "parallel": FieldSchema(
                name="parallel",
                type=FieldType.BOOLEAN,
                description="i18n:fields.SplitNode.parallel",
                default=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=False,
                expected_type="bool",
            ),
            "delay_ms": FieldSchema(
                name="delay_ms",
                type=FieldType.INTEGER,
                description="i18n:fields.SplitNode.delay_ms",
                default=0,
                min_value=0,
                max_value=60000,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="0",
                example=500,
                expected_type="int",
                helper_text="i18n:fields.SplitNode.delay_ms_helper",
            ),
            "continue_on_error": FieldSchema(
                name="continue_on_error",
                type=FieldType.BOOLEAN,
                description="i18n:fields.SplitNode.continue_on_error",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=True,
                expected_type="bool",
            ),
        }


class AggregateNode(BaseNode):
    """
    Aggregate individual items into a list

    Collects results from SplitNode branches and outputs as a list.
    Supports various aggregation modes: collect, filter, sum, avg, min, max, count, first, last.
    """

    type: Literal["AggregateNode"] = "AggregateNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.AggregateNode.description"

    _img_url: ClassVar[str] = ""

    # AggregateNode specific config
    mode: Literal["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"] = Field(
        default="collect",
        description="Aggregation mode"
    )
    filter_field: Optional[str] = Field(
        default="passed",
        description="Field to filter by (for filter mode)"
    )
    value_field: Optional[str] = Field(
        default="value",
        description="Field to aggregate (for sum/avg/min/max modes)"
    )

    _inputs: List[InputPort] = [
        InputPort(name="item", type="any", description="i18n:ports.aggregate_item")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="array", type="array", description="i18n:ports.aggregate_array"),
        OutputPort(name="value", type="number", description="i18n:ports.aggregate_value"),
        OutputPort(name="count", type="integer", description="i18n:ports.aggregate_count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="i18n:fields.AggregateNode.mode",
                default="collect",
                enum_values=["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"],
                enum_labels={
                    "collect": "i18n:enums.aggregate_mode.collect",
                    "filter": "i18n:enums.aggregate_mode.filter",
                    "sum": "i18n:enums.aggregate_mode.sum",
                    "avg": "i18n:enums.aggregate_mode.avg",
                    "min": "i18n:enums.aggregate_mode.min",
                    "max": "i18n:enums.aggregate_mode.max",
                    "count": "i18n:enums.aggregate_mode.count",
                    "first": "i18n:enums.aggregate_mode.first",
                    "last": "i18n:enums.aggregate_mode.last",
                },
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="collect",
                expected_type="str",
            ),
            "filter_field": FieldSchema(
                name="filter_field",
                type=FieldType.STRING,
                description="i18n:fields.AggregateNode.filter_field",
                default="passed",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="passed",
                example="passed",
                expected_type="str",
                helper_text="i18n:fields.AggregateNode.filter_field_helper",
            ),
            "value_field": FieldSchema(
                name="value_field",
                type=FieldType.STRING,
                description="i18n:fields.AggregateNode.value_field",
                default="value",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="value",
                example="value",
                expected_type="str",
                helper_text="i18n:fields.AggregateNode.value_field_helper",
            ),
        }


class IfNode(BaseNode):
    """
    조건 분기 노드

    left와 right 값을 operator로 비교하여 true/false 브랜치로 실행 흐름을 분기합니다.
    조건이 참이면 true 포트로, 거짓이면 false 포트로 데이터가 전달됩니다.

    Edge에 from_port를 지정하여 분기 경로를 설정합니다:
    - {"from": "if1", "to": "order", "from_port": "true"}
    - {"from": "if1", "to": "notify", "from_port": "false"}
    """

    type: Literal["IfNode"] = "IfNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.IfNode.description"

    _img_url: ClassVar[str] = ""

    # 비교 연산 필드
    left: Any = Field(default=None, description="왼쪽 피연산자 (표현식 바인딩 가능)")
    operator: Literal[
        "==", "!=", ">", ">=", "<", "<=",
        "in", "not_in",
        "contains", "not_contains",
        "is_empty", "is_not_empty",
    ] = Field(default="==", description="비교 연산자")
    right: Any = Field(default=None, description="오른쪽 피연산자 (표현식 바인딩 가능)")

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="true", type="any", description="i18n:ports.if_true"),
        OutputPort(name="false", type="any", description="i18n:ports.if_false"),
        OutputPort(name="result", type="boolean", description="i18n:ports.if_result"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode,
        )
        return {
            "left": FieldSchema(
                name="left",
                type=FieldType.STRING,
                description="i18n:fields.IfNode.left",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.balance }}",
                example="{{ nodes.account.balance }}",
                expected_type="any",
            ),
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.IfNode.operator",
                default="==",
                enum_values=[
                    "==", "!=", ">", ">=", "<", "<=",
                    "in", "not_in",
                    "contains", "not_contains",
                    "is_empty", "is_not_empty",
                ],
                enum_labels={
                    "==": "i18n:enums.if_operator.eq",
                    "!=": "i18n:enums.if_operator.ne",
                    ">": "i18n:enums.if_operator.gt",
                    ">=": "i18n:enums.if_operator.gte",
                    "<": "i18n:enums.if_operator.lt",
                    "<=": "i18n:enums.if_operator.lte",
                    "in": "i18n:enums.if_operator.in",
                    "not_in": "i18n:enums.if_operator.not_in",
                    "contains": "i18n:enums.if_operator.contains",
                    "not_contains": "i18n:enums.if_operator.not_contains",
                    "is_empty": "i18n:enums.if_operator.is_empty",
                    "is_not_empty": "i18n:enums.if_operator.is_not_empty",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example=">=",
            ),
            "right": FieldSchema(
                name="right",
                type=FieldType.STRING,
                description="i18n:fields.IfNode.right",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="1000000",
                example="1000000",
                expected_type="any",
                visible_when={
                    "operator": [
                        "==", "!=", ">", ">=", "<", "<=",
                        "in", "not_in", "contains", "not_contains",
                    ],
                },
            ),
        }
