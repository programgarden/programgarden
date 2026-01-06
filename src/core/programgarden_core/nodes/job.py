"""
ProgramGarden Core - Job Nodes

Job control nodes:
- DeployNode: Strategy deployment (live/paper trading)
- TradingHaltNode: Trading halt
- JobControlNode: Job state control
"""

from typing import Optional, List, Literal
from pydantic import Field

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
