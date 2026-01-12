"""
ProgramGarden Core - Job Nodes

Job control nodes:
- DeployNode: Strategy deployment (live/paper trading)
- TradingHaltNode: Trading halt
- JobControlNode: Job state control
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


class DeployNode(BaseNode):
    """
    Strategy deployment node

    Deploy strategy to live or paper trading after backtest validation
    """

    type: Literal["DeployNode"] = "DeployNode"
    category: NodeCategory = NodeCategory.JOB
    description: str = "i18n:nodes.DeployNode.description"

    # DeployNode specific config
    mode: Literal["live", "paper", "dry_run"] = Field(
        default="paper",
        description="Deployment mode (live: real trading, paper: paper trading, dry_run: test)",
    )
    paper_trading: bool = Field(
        default=True,
        description="Paper trading flag",
    )
    schedule_type: Literal["immediate", "scheduled"] = Field(
        default="immediate",
        description="Deployment timing",
    )
    scheduled_time: Optional[str] = Field(
        default=None,
        description="Scheduled deployment time (ISO 8601 format)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
        ),
        InputPort(
            name="strategy",
            type="strategy",
            description="i18n:ports.strategy",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="deploy_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="job_id",
            type="string",
            description="i18n:ports.job_id",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 배포 설정 ===
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="Deployment mode",
                default="paper",
                enum_values=["live", "paper", "dry_run"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "paper_trading": FieldSchema(
                name="paper_trading",
                type=FieldType.BOOLEAN,
                description="Paper trading flag",
                default=True,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "schedule_type": FieldSchema(
                name="schedule_type",
                type=FieldType.ENUM,
                description="Deployment timing",
                default="immediate",
                enum_values=["immediate", "scheduled"],
                category=FieldCategory.SETTINGS,
            ),
            "scheduled_time": FieldSchema(
                name="scheduled_time",
                type=FieldType.STRING,
                description="Scheduled time (ISO 8601)",
                required=False,
                category=FieldCategory.SETTINGS,
            ),
        }


class TradingHaltNode(BaseNode):
    """
    Trading halt node

    Temporarily halt trading when risk limits are exceeded
    """

    type: Literal["TradingHaltNode"] = "TradingHaltNode"
    category: NodeCategory = NodeCategory.JOB
    description: str = "i18n:nodes.TradingHaltNode.description"

    # TradingHaltNode specific config
    duration_hours: float = Field(
        default=24,
        description="Halt duration (hours)",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Halt reason",
    )
    resume_condition: Optional[str] = Field(
        default=None,
        description="Resume condition (e.g., 'next_trading_day')",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="halted",
            type="signal",
            description="i18n:ports.halted",
        ),
        OutputPort(
            name="resume_at",
            type="datetime",
            description="i18n:ports.resume_at",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 설정 ===
            "duration_hours": FieldSchema(
                name="duration_hours",
                type=FieldType.NUMBER,
                description="Halt duration (hours)",
                default=24,
                min_value=0.1,
                category=FieldCategory.PARAMETERS,
            ),
            "reason": FieldSchema(
                name="reason",
                type=FieldType.STRING,
                description="Halt reason",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "resume_condition": FieldSchema(
                name="resume_condition",
                type=FieldType.STRING,
                description="Resume condition (e.g., 'next_trading_day')",
                required=False,
                category=FieldCategory.SETTINGS,
            ),
        }


class JobControlNode(BaseNode):
    """
    Job state control node

    Control running Job: pause, resume, stop
    """

    type: Literal["JobControlNode"] = "JobControlNode"
    category: NodeCategory = NodeCategory.JOB
    description: str = "i18n:nodes.JobControlNode.description"

    # JobControlNode specific config
    action: Literal["pause", "resume", "stop", "restart"] = Field(
        description="Control action",
    )
    target_job_id: Optional[str] = Field(
        default=None,
        description="Target Job ID (None for current Job)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="job_control_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="new_state",
            type="string",
            description="New Job state",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 모두 핵심 제어 설정 ===
            "action": FieldSchema(
                name="action",
                type=FieldType.ENUM,
                description="Control action",
                enum_values=["pause", "resume", "stop", "restart"],
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "target_job_id": FieldSchema(
                name="target_job_id",
                type=FieldType.STRING,
                description="Target Job ID (None for current Job)",
                required=False,
                category=FieldCategory.PARAMETERS,
            ),
        }