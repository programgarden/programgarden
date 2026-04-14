"""
ProgramGarden Core - Trigger Nodes

Trigger/filter nodes:
- ScheduleNode: Cron schedule trigger
- TradingHoursFilterNode: Trading hours filter
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
    category: NodeCategory = NodeCategory.SCHEDULE
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
    max_duration_hours: float = Field(
        default=24.0,
        description="최대 실행 시간 (시간). 초과 시 스케줄 자동 종료.",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="trigger",
            type="signal",
            description="i18n:ports.trigger",
            example={"fired_at": "2026-04-14T09:30:00-04:00", "cycle_index": 0},
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 핵심 스케줄 설정 ===
            "cron": FieldSchema(
                name="cron",
                type=FieldType.STRING,
                description="Cron expression. Format: minute hour day month weekday. Examples: */5 * * * * (every 5 min), 0 9 * * 1-5 (9am weekdays)",
                default="*/5 * * * *",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="*/5 * * * *",
                expected_type="str",
            ),
            "timezone": FieldSchema(
                name="timezone",
                type=FieldType.STRING,
                description="Timezone for cron schedule. Use IANA timezone names.",
                default="America/New_York",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="America/New_York",
                expected_type="str",
            ),
            # === SETTINGS: 부가 설정 ===
            "enabled": FieldSchema(
                name="enabled",
                type=FieldType.BOOLEAN,
                description="Enable/disable the schedule. When disabled, trigger will not fire.",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.SETTINGS,
                example=True,
            ),
            "max_duration_hours": FieldSchema(
                name="max_duration_hours",
                type=FieldType.NUMBER,
                description="i18n:fields.ScheduleNode.max_duration_hours",
                default=24.0,
                min_value=0.1,
                max_value=720.0,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.SETTINGS,
                expected_type="float",
                example=24.0,
            ),
        }


class TradingHoursFilterNode(BaseNode):
    """
    Trading hours filter node

    Passes signals only within specified trading hours
    """

    type: Literal["TradingHoursFilterNode"] = "TradingHoursFilterNode"
    category: NodeCategory = NodeCategory.SCHEDULE
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
    max_wait_hours: float = Field(
        default=24.0,
        description="최대 대기 시간 (시간). 초과 시 timeout으로 처리.",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="passed",
            type="signal",
            description="i18n:ports.passed",
            example={"passed": True, "reason": "within_trading_hours"},
        ),
        OutputPort(
            name="blocked",
            type="signal",
            description="i18n:ports.blocked",
            example={"passed": False, "reason": "outside_trading_hours"},
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 핵심 거래시간 설정 ===
            "start": FieldSchema(
                name="start",
                type=FieldType.STRING,
                description="Start time in HH:MM format (24-hour). Signals before this time are blocked.",
                default="09:30",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="09:30",
                expected_type="str",
            ),
            "end": FieldSchema(
                name="end",
                type=FieldType.STRING,
                description="End time in HH:MM format (24-hour). Signals after this time are blocked.",
                default="16:00",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="16:00",
                expected_type="str",
            ),
            "days": FieldSchema(
                name="days",
                type=FieldType.ARRAY,
                description="Active trading days. Options: mon, tue, wed, thu, fri, sat, sun",
                default=["mon", "tue", "wed", "thu", "fri"],
                array_item_type=FieldType.STRING,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=["mon", "tue", "wed", "thu", "fri"],
                expected_type="list[str]",
            ),
            # === SETTINGS: 부가 설정 ===
            "timezone": FieldSchema(
                name="timezone",
                type=FieldType.STRING,
                description="Timezone for time comparison. Use IANA timezone names.",
                default="America/New_York",
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="America/New_York",
                expected_type="str",
            ),
            "max_wait_hours": FieldSchema(
                name="max_wait_hours",
                type=FieldType.NUMBER,
                description="i18n:fields.TradingHoursFilterNode.max_wait_hours",
                default=24.0,
                min_value=0.1,
                max_value=168.0,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.SETTINGS,
                expected_type="float",
                example=24.0,
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
        - max_wait_hours 초과 시: timeout 반환
        - 워크플로우 종료 시: graceful shutdown
        """
        import time as _time
        # dry_run: 거래시간 대기 없이 즉시 통과
        if getattr(context, "is_dry_run", False):
            context.log("info", "[dry_run] TradingHoursFilter bypassed", self.id)
            return {"passed": True, "reason": "dry_run_bypass"}

        check_interval = 60  # 1분마다 체크
        wait_start = _time.monotonic()
        max_wait_sec = self.max_wait_hours * 3600

        while not self._is_trading_hours():
            # graceful shutdown 체크
            if hasattr(context, 'is_running') and not context.is_running:
                context.log("info", "Shutdown requested, exiting trading hours wait", self.id)
                return {"passed": False, "reason": "shutdown"}

            # M-7: max_wait_hours 초과 체크
            if (_time.monotonic() - wait_start) >= max_wait_sec:
                context.log(
                    "warning",
                    f"거래시간 대기 timeout: max_wait_hours={self.max_wait_hours}h 초과",
                    self.id,
                )
                return {"passed": False, "reason": "timeout"}

            context.log("debug", f"Outside trading hours, waiting... (next check in {check_interval}s)", self.id)
            await asyncio.sleep(check_interval)

        context.log("info", "Trading hours active, passing through", self.id)
        return {"passed": True}
