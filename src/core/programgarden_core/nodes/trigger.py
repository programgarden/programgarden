"""
ProgramGarden Core - Trigger Nodes

Trigger/filter nodes:
- ScheduleNode: Cron schedule trigger
- TradingHoursFilterNode: Trading hours filter
- ExchangeStatusNode: Exchange status check
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


class ScheduleNode(BaseNode):
    """
    Cron schedule trigger node

    Emits trigger signal according to specified cron expression
    """

    type: Literal["ScheduleNode"] = "ScheduleNode"
    category: NodeCategory = NodeCategory.TRIGGER
    description: str = "i18n:nodes.ScheduleNode.description"

    # ScheduleNode specific config
    cron: str = Field(
        default="*/5 * * * *",
        description="Cron expression (e.g., */5 * * * * = every 5 minutes)",
    )
    timezone: str = Field(
        default="America/New_York", description="Timezone (e.g., America/New_York, Asia/Seoul)"
    )
    enabled: bool = Field(default=True, description="Schedule enabled")

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="trigger", type="signal", description="i18n:ports.trigger")
    ]
    _field_schema: ClassVar[Dict[str, FieldSchema]] = {
        "cron": FieldSchema(
            name="cron",
            type=FieldType.STRING,
            description="i18n:fields.ScheduleNode.cron",
            default="*/5 * * * *",
            required=True,
            bindable=False,
        ),
        "timezone": FieldSchema(
            name="timezone",
            type=FieldType.STRING,
            description="i18n:fields.ScheduleNode.timezone",
            default="America/New_York",
            bindable=False,
        ),
        "enabled": FieldSchema(
            name="enabled",
            type=FieldType.BOOLEAN,
            description="i18n:fields.ScheduleNode.enabled",
            default=True,
            bindable=False,
        ),
    }


class TradingHoursFilterNode(BaseNode):
    """
    Trading hours filter node

    Passes signals only within specified trading hours
    """

    type: Literal["TradingHoursFilterNode"] = "TradingHoursFilterNode"
    category: NodeCategory = NodeCategory.TRIGGER
    description: str = "i18n:nodes.TradingHoursFilterNode.description"

    # TradingHoursFilterNode specific config
    start: str = Field(default="09:30", description="Start time (HH:MM)")
    end: str = Field(default="16:00", description="End time (HH:MM)")
    timezone: str = Field(
        default="America/New_York", description="Timezone (e.g., America/New_York)"
    )
    days: List[str] = Field(
        default=["mon", "tue", "wed", "thu", "fri"],
        description="Active days (mon, tue, wed, thu, fri, sat, sun)",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="passed", type="signal", description="i18n:ports.passed"
        ),
        OutputPort(
            name="blocked", type="signal", description="i18n:ports.blocked"
        ),
    ]


class ExchangeStatusNode(BaseNode):
    """
    Exchange status check node

    Checks exchange open/close/holiday status
    """

    type: Literal["ExchangeStatusNode"] = "ExchangeStatusNode"
    category: NodeCategory = NodeCategory.TRIGGER
    description: str = "i18n:nodes.ExchangeStatusNode.description"

    # ExchangeStatusNode specific config
    exchange: str = Field(
        default="NYSE", description="Exchange code (NYSE, NASDAQ, CME, etc.)"
    )
    check_holidays: bool = Field(
        default=True, description="Check holidays"
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="connection",
            type="broker_connection",
            description="i18n:ports.connection",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="open", type="signal", description="i18n:ports.open"),
        OutputPort(name="closed", type="signal", description="i18n:ports.closed"),
        OutputPort(name="holiday", type="signal", description="i18n:ports.holiday"),
    ]
