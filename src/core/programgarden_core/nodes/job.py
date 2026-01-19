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
    category: NodeCategory = NodeCategory.SYSTEM
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 핵심 배포 설정 ===
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="Deployment mode. live: real trading with real money. paper: simulated trading. dry_run: test without execution.",
                default="paper",
                enum_values=["live", "paper", "dry_run"],
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="paper",
                expected_type="str",
            ),
            "paper_trading": FieldSchema(
                name="paper_trading",
                type=FieldType.BOOLEAN,
                description="Enable paper trading. When true, orders are simulated.",
                default=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            # === SETTINGS: 부가 설정 ===
            "schedule_type": FieldSchema(
                name="schedule_type",
                type=FieldType.ENUM,
                description="Deployment timing. immediate: deploy now. scheduled: deploy at specified time.",
                default="immediate",
                enum_values=["immediate", "scheduled"],
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="immediate",
                expected_type="str",
            ),
            "scheduled_time": FieldSchema(
                name="scheduled_time",
                type=FieldType.STRING,
                description="Scheduled deployment time in ISO 8601 format. Only used when schedule_type='scheduled'.",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="2024-01-15T09:30:00-05:00",
                expected_type="str",
            ),
        }


class TradingHaltNode(BaseNode):
    """
    Trading halt node

    Temporarily halt trading when risk limits are exceeded
    """

    type: Literal["TradingHaltNode"] = "TradingHaltNode"
    category: NodeCategory = NodeCategory.SYSTEM
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 핵심 설정 ===
            "duration_hours": FieldSchema(
                name="duration_hours",
                type=FieldType.NUMBER,
                description="Trading halt duration in hours. Trading resumes after this period.",
                default=24,
                min_value=0.1,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=24,
                expected_type="float",
            ),
            "reason": FieldSchema(
                name="reason",
                type=FieldType.STRING,
                description="Reason for trading halt. Logged for audit trail.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="Daily loss limit exceeded",
                example_binding="{{ nodes.riskGuard.halt_reason }}",
                bindable_sources=["RiskGuardNode.halt_reason"],
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "resume_condition": FieldSchema(
                name="resume_condition",
                type=FieldType.STRING,
                description="Condition for automatic resume. Options: 'next_trading_day', 'manual', or custom condition.",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="next_trading_day",
                expected_type="str",
            ),
        }


class JobControlNode(BaseNode):
    """
    Job state control node

    Control running Job: pause, resume, stop
    """

    type: Literal["JobControlNode"] = "JobControlNode"
    category: NodeCategory = NodeCategory.SYSTEM
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
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 모두 핵심 제어 설정 ===
            "action": FieldSchema(
                name="action",
                type=FieldType.ENUM,
                description="Job control action. pause: temporarily stop trading. resume: continue paused job. stop: permanently stop job. restart: stop and restart job.",
                enum_values=["pause", "resume", "stop", "restart"],
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="pause",
                expected_type="str",
            ),
            "target_job_id": FieldSchema(
                name="target_job_id",
                type=FieldType.STRING,
                description="Target Job ID to control. Leave empty to control current job.",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                example="job_abc123",
                expected_type="str",
            ),
        }