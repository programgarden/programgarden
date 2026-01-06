"""
ProgramGarden Core - Event Nodes

Event/alert nodes:
- EventHandlerNode: Order event handling
- ErrorHandlerNode: Error handling and recovery
- AlertNode: Send notifications
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class EventHandlerNode(BaseNode):
    """
    Order event handler node

    Performs follow-up actions when fill/reject/cancel events occur
    """

    type: Literal["EventHandlerNode"] = "EventHandlerNode"
    category: NodeCategory = NodeCategory.EVENT
    description: str = "i18n:nodes.EventHandlerNode.description"

    # EventHandlerNode specific config
    event: Literal["filled", "rejected", "cancelled", "partial_filled", "all"] = Field(
        default="all",
        description="Event type to handle",
    )
    actions: List[str] = Field(
        default=["log"],
        description="Actions to perform (log, notify, trigger, etc.)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="order_event",
            description="i18n:ports.event",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="event",
            type="event_data",
            description="i18n:ports.event",
        ),
        OutputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
        ),
    ]


class ErrorHandlerNode(BaseNode):
    """
    Error handling and recovery node

    Error handling and recovery logic during execution
    """

    type: Literal["ErrorHandlerNode"] = "ErrorHandlerNode"
    category: NodeCategory = NodeCategory.EVENT
    description: str = "i18n:nodes.ErrorHandlerNode.description"

    # ErrorHandlerNode specific config
    error_types: List[str] = Field(
        default=["all"],
        description="Error types to handle (connection, order, validation, all, etc.)",
    )
    retry_count: int = Field(
        default=3,
        description="Retry count",
    )
    retry_delay_sec: int = Field(
        default=5,
        description="Retry delay (seconds)",
    )
    fallback_action: Literal["ignore", "alert", "pause_job", "cancel_orders"] = Field(
        default="alert",
        description="Fallback action when retries fail",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="error",
            type="error_event",
            description="i18n:ports.error_data",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="recovered",
            type="signal",
            description="i18n:ports.recovered",
        ),
        OutputPort(
            name="failed",
            type="signal",
            description="i18n:ports.failed",
        ),
        OutputPort(
            name="error_data",
            type="error_data",
            description="i18n:ports.error_data",
        ),
    ]


class AlertNode(BaseNode):
    """
    Alert notification node

    Send notifications via Slack, Telegram, Email, Webhook, etc.
    """

    type: Literal["AlertNode"] = "AlertNode"
    category: NodeCategory = NodeCategory.EVENT
    description: str = "i18n:nodes.AlertNode.description"

    # AlertNode specific config
    channel: Literal["slack", "telegram", "email", "webhook"] = Field(
        default="slack",
        description="Notification channel",
    )
    on: List[str] = Field(
        default=["order_filled", "risk_triggered", "error"],
        description="Event types to trigger notification",
    )
    template: Optional[str] = Field(
        default=None,
        description="Message template (variables: {symbol}, {side}, {price}, {quantity}, etc.)",
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL (when channel=webhook)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="event",
            type="event_data",
            description="i18n:ports.event",
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="Notification sent signal",
        ),
    ]
