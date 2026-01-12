"""
ProgramGarden Core - Trigger Nodes

Trigger/filter nodes:
- ScheduleNode: Cron schedule trigger
- TradingHoursFilterNode: Trading hours filter
- ExchangeStatusNode: Exchange status check
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from datetime import datetime
import asyncio

from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.bases.context import BaseExecutionContext
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 스케줄 설정 ===
            "cron": FieldSchema(
                name="cron",
                type=FieldType.STRING,
                description="i18n:fields.ScheduleNode.cron",
                default="*/5 * * * *",
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "timezone": FieldSchema(
                name="timezone",
                type=FieldType.STRING,
                description="i18n:fields.ScheduleNode.timezone",
                default="America/New_York",
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "enabled": FieldSchema(
                name="enabled",
                type=FieldType.BOOLEAN,
                description="i18n:fields.ScheduleNode.enabled",
                default=True,
                bindable=False,
                category=FieldCategory.SETTINGS,
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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 거래시간 설정 ===
            "start": FieldSchema(
                name="start",
                type=FieldType.STRING,
                description="Start time (HH:MM)",
                default="09:30",
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "end": FieldSchema(
                name="end",
                type=FieldType.STRING,
                description="End time (HH:MM)",
                default="16:00",
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            "days": FieldSchema(
                name="days",
                type=FieldType.ARRAY,
                description="Active days",
                default=["mon", "tue", "wed", "thu", "fri"],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "timezone": FieldSchema(
                name="timezone",
                type=FieldType.STRING,
                description="Timezone",
                default="America/New_York",
                category=FieldCategory.SETTINGS,
            ),
        }

    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        try:
            import pytz
        except ImportError:
            # pytz 없으면 UTC 기준으로 체크
            now = datetime.utcnow()
            tz = None
        else:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
        
        # 요일 체크
        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        active_weekdays = [day_map[d.lower()] for d in self.days if d.lower() in day_map]
        if now.weekday() not in active_weekdays:
            return False
        
        # 시간 체크
        try:
            start_h, start_m = map(int, self.start.split(":"))
            end_h, end_m = map(int, self.end.split(":"))
        except ValueError:
            # 파싱 실패 시 통과
            return True
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        return start_minutes <= current_minutes <= end_minutes

    async def execute(self, context: "BaseExecutionContext") -> Dict[str, Any]:
        """
        Wait until trading hours, then pass through.
        
        - 거래시간 내: 즉시 통과
        - 거래시간 외: 거래시간이 될 때까지 대기
        - 워크플로우 종료 시: graceful shutdown
        """
        check_interval = 60  # 1분마다 체크
        
        while not self._is_trading_hours():
            # graceful shutdown 체크
            if hasattr(context, 'is_running') and not context.is_running:
                context.log("info", "Shutdown requested, exiting trading hours wait", self.id)
                return {"passed": False, "reason": "shutdown"}
            
            context.log("debug", f"Outside trading hours, waiting... (next check in {check_interval}s)", self.id)
            await asyncio.sleep(check_interval)
        
        context.log("info", "Trading hours active, passing through", self.id)
        return {"passed": True}


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

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 핵심 거래소 설정 ===
            "exchange": FieldSchema(
                name="exchange",
                type=FieldType.STRING,
                description="Exchange code (NYSE, NASDAQ, CME, etc.)",
                default="NYSE",
                required=True,
                category=FieldCategory.PARAMETERS,
            ),
            # === SETTINGS: 부가 설정 ===
            "check_holidays": FieldSchema(
                name="check_holidays",
                type=FieldType.BOOLEAN,
                description="Check holidays",
                default=True,
                category=FieldCategory.SETTINGS,
            ),
        }
