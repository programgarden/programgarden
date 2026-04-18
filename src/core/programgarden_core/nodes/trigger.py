"""
ProgramGarden Core - Trigger Nodes

Trigger/filter nodes:
- ScheduleNode: Cron schedule trigger
- TradingHoursFilterNode: Trading hours filter
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING, ClassVar
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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Run the main flow on a cron schedule (every N minutes, daily at 09:30 ET, weekly market close, …)",
            "Bound long-running workflows with max_duration_hours to avoid runaway schedulers",
            "Combine with TradingHoursFilterNode to fire only on weekdays within market hours",
        ],
        "when_not_to_use": [
            "Event-driven flows (realtime ticks, order fills) — use Real*Node sources instead",
            "One-shot workflows — StartNode alone is enough; ScheduleNode would loop forever",
            "Sub-minute cadence — cron's minimum granularity is 1 minute; use ThrottleNode for sub-minute pacing",
        ],
        "typical_scenarios": [
            "Start → ScheduleNode (0 9 * * 1-5) → trading body (fires 09:00 ET on weekdays)",
            "Start → ScheduleNode (*/15 * * * *) → TradingHoursFilterNode → signals",
            "Start → ScheduleNode (0 */4 * * *) → portfolio snapshot → TableDisplayNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Standard 5-field cron expression — minute / hour / day / month / weekday",
        "Timezone-aware (IANA names) — 'America/New_York', 'Asia/Seoul', 'UTC'",
        "max_duration_hours caps total runtime; the scheduler exits cleanly at the limit",
        "enabled=False freezes the trigger without removing the node from the DAG",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using ScheduleNode with `* * * * *` (every minute) to poll cheap data",
            "reason": "Every fire triggers the full main flow — brokers, LS TRs, downstream plugins. Even if cheap per run, it accumulates rate-limit pressure.",
            "alternative": "Increase the interval (e.g. `*/5 * * * *`) or use a realtime source (Real*Node) with ThrottleNode for downstream pacing.",
        },
        {
            "pattern": "Missing timezone — relying on the server default",
            "reason": "Different environments / deployments may default to UTC, causing `0 9 * * *` to fire at the wrong hour.",
            "alternative": "Always set timezone to the intended market tz: 'America/New_York' for US, 'Asia/Seoul' for KRX, 'Asia/Hong_Kong' for HKEX.",
        },
        {
            "pattern": "No TradingHoursFilterNode downstream for time-sensitive trading",
            "reason": "Cron fires exactly at the cron cadence, including weekends and holidays; orders may slip onto a closed market.",
            "alternative": "Chain `ScheduleNode → TradingHoursFilterNode (from_port='passed') → trading body` so cron-after-hours is silently blocked.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "9:30 ET weekday open trigger",
            "description": "Runs the trading body once at 09:30 America/New_York, Monday through Friday.",
            "workflow_snippet": {
                "id": "schedule-us-open",
                "name": "US market-open schedule",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "cron", "type": "ScheduleNode", "cron": "30 9 * * 1-5", "timezone": "America/New_York"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "cron"},
                    {"from": "cron", "to": "broker"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Every weekday at 09:30 ET, broker session opens and the account is queried. Off-schedule cycles are skipped.",
        },
        {
            "title": "Every 15 minutes intraday, trading-hours gated",
            "description": "ScheduleNode fires every 15 minutes; TradingHoursFilterNode only forwards during 09:30–16:00 ET; downstream runs signals and displays the result.",
            "workflow_snippet": {
                "id": "schedule-intraday",
                "name": "Intraday 15-min schedule",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "cron", "type": "ScheduleNode", "cron": "*/15 * * * *", "timezone": "America/New_York"},
                    {"id": "hours", "type": "TradingHoursFilterNode", "start": "09:30", "end": "16:00", "timezone": "America/New_York", "days": ["mon", "tue", "wed", "thu", "fri"]},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "SPY", "exchange": "NYSE"}]},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "cron"},
                    {"from": "cron", "to": "hours"},
                    {"from": "hours", "to": "broker", "from_port": "passed"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "market"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Every 15 minutes the cron fires; trading-hours gate passes only 09:30–16:00 weekdays; SPY quote fetched on passing cycles.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "No data inputs. All behavior is configured via `cron`, `timezone`, `enabled`, `max_duration_hours`.",
        "output_consumption": "`trigger` output carries `{fired_at, cycle_index}`. Downstream nodes usually just need an incoming edge; explicit binding is optional.",
        "common_combinations": [
            "StartNode → ScheduleNode → trading body (plain cron workflow)",
            "StartNode → ScheduleNode → TradingHoursFilterNode → body (market-hours gate)",
            "StartNode → ScheduleNode → RealMarketDataNode (subscribe once per cycle)",
        ],
        "pitfalls": [
            "Always set `timezone` explicitly — server defaults are not portable",
            "Pair with TradingHoursFilterNode when the cron expression does not already encode market hours",
            "max_duration_hours caps the total runtime; for indefinite bots set it generously (up to 720h)",
        ],
    }

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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Gate a scheduled or realtime flow so it only acts during market hours",
            "Separate weekday / weekend logic without hard-coding the cron expression",
            "Enforce a start-of-day / end-of-day window around a fixed trading body",
        ],
        "when_not_to_use": [
            "Actual exchange status (holidays, circuit breakers) — use MarketStatusNode (JIF-backed) for authoritative market state",
            "Strict cron cadence without time windowing — ScheduleNode alone is enough",
            "Realtime-only workflows that naturally stop outside market hours (no ticks arrive) — filter adds no value",
        ],
        "typical_scenarios": [
            "ScheduleNode → TradingHoursFilterNode → trading body (passed branch)",
            "TradingHoursFilterNode → IfNode(reason='...') for per-reason branching",
            "Start → TradingHoursFilterNode → long-running realtime subscription (cleanup at close)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Configurable start / end in HH:MM form and IANA timezone",
        "`days` whitelist supports weekend-only or weekday-only flows",
        "Dual outputs: `passed` (within hours) and `blocked` (outside) for explicit branching",
        "max_wait_hours safeguards long waits — the node timeouts instead of stalling forever",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using TradingHoursFilterNode as a holiday / circuit-breaker check",
            "reason": "The node only knows HH:MM windows + day-of-week; it has no knowledge of US federal holidays or KRX short-sale suspensions.",
            "alternative": "Chain MarketStatusNode (JIF) before TradingHoursFilterNode for authoritative exchange state.",
        },
        {
            "pattern": "Missing timezone — defaulting to server time",
            "reason": "A 'start=09:30' window interpreted in UTC would open 4–5 hours off US market open, causing workflows to gate incorrectly.",
            "alternative": "Always set timezone to the target market's IANA name (America/New_York, Asia/Seoul, Asia/Hong_Kong, Asia/Tokyo).",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Pass signals only during US market hours",
            "description": "Schedule fires every 5 minutes; TradingHoursFilter passes only 09:30–16:00 on weekdays; downstream trading body runs only during hours.",
            "workflow_snippet": {
                "id": "hours-filter-us",
                "name": "Schedule + trading hours",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "cron", "type": "ScheduleNode", "cron": "*/5 * * * *", "timezone": "America/New_York"},
                    {"id": "hours", "type": "TradingHoursFilterNode", "start": "09:30", "end": "16:00", "timezone": "America/New_York", "days": ["mon", "tue", "wed", "thu", "fri"]},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "cron"},
                    {"from": "cron", "to": "hours"},
                    {"from": "hours", "to": "broker", "from_port": "passed"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Cron fires every 5 min; account query runs only during US trading hours on weekdays. Off-hours cycles hit the blocked branch and skip downstream.",
        },
        {
            "title": "Branch on blocked path for after-hours notification",
            "description": "TradingHoursFilterNode forks: passed branch runs trading body, blocked branch sends an after-hours notice.",
            "workflow_snippet": {
                "id": "hours-filter-notify",
                "name": "Trading hours fork",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "cron", "type": "ScheduleNode", "cron": "0 * * * *", "timezone": "America/New_York"},
                    {"id": "hours", "type": "TradingHoursFilterNode", "start": "09:30", "end": "16:00", "timezone": "America/New_York", "days": ["mon", "tue", "wed", "thu", "fri"]},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "closed_notice", "type": "SummaryDisplayNode", "title": "Market closed", "data": {"reason": "outside_hours"}},
                ],
                "edges": [
                    {"from": "start", "to": "cron"},
                    {"from": "cron", "to": "hours"},
                    {"from": "hours", "to": "broker", "from_port": "passed"},
                    {"from": "broker", "to": "account"},
                    {"from": "hours", "to": "closed_notice", "from_port": "blocked"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Hourly cron; within hours → account query; outside hours → SummaryDisplay renders the closed notice.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Trigger edge from upstream (ScheduleNode or StartNode). Window is configured via start / end / timezone / days.",
        "output_consumption": "`passed` port runs during-hours branches; `blocked` runs after-hours branches. Use edge `from_port` to pick which downstream fires.",
        "common_combinations": [
            "ScheduleNode → TradingHoursFilterNode → trading body",
            "TradingHoursFilterNode → OverseasStockRealMarketDataNode (start realtime only in-hours)",
            "TradingHoursFilterNode → IfNode on `reason` field for per-state branching",
        ],
        "pitfalls": [
            "Always specify `timezone` — server default is not portable",
            "For holidays / CB / market status use MarketStatusNode (JIF) instead of or alongside this node",
            "`days` names are lowercase 3-letter: mon / tue / wed / thu / fri / sat / sun",
        ],
    }

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
