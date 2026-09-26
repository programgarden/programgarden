"""Immediate, explicit time-window checks for scheduled and pre-order gates."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, ClassVar, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from programgarden_core.nodes.base import BaseNode, InputPort, NodeCategory, OutputPort


class SessionWindow(BaseModel):
    """A local interval with inclusive start and exclusive end."""
    start: str
    end: str

    @field_validator('start', 'end')
    @classmethod
    def valid_time(cls, value: str) -> str:
        if len(value) != 5 or value[2] != ':' or not (value[:2]+value[3:]).isascii() or not (value[:2]+value[3:]).isdigit():
            raise ValueError('Session time must be HH:MM')
        if int(value[:2]) > 23 or int(value[3:]) > 59:
            raise ValueError('Session time is out of range')
        return value

    @model_validator(mode='after')
    def nonempty(self):
        if self.start == self.end:
            raise ValueError('Session start and end must differ')
        return self


class SessionGateNode(BaseNode):
    """Return a time decision immediately; use IfNode to enforce it.

    This does not query an exchange calendar, infer holidays, wait for the next
    session, or grant trading authority. Recheck near the order boundary.
    """
    type: Literal['SessionGateNode'] = 'SessionGateNode'
    category: NodeCategory = NodeCategory.SCHEDULE
    description: str = 'i18n:nodes.SessionGateNode.description'
    timezone: str = Field(..., description='i18n:nodes.SessionGateNode.timezone')
    windows: list[SessionWindow] = Field(..., min_length=1, description='i18n:nodes.SessionGateNode.windows')
    days: list[Literal['mon','tue','wed','thu','fri','sat','sun']] = Field(..., min_length=1, description='i18n:nodes.SessionGateNode.days')
    closed_dates: list[str] = Field(default_factory=list, description='i18n:nodes.SessionGateNode.closed_dates')

    _inputs: list[InputPort] = [InputPort(name='trigger',type='signal',required=False,description='i18n:nodes.SessionGateNode.trigger')]
    _outputs: list[OutputPort] = [OutputPort(name=k,type=t,description=d) for k,t,d in [
        ('allowed','boolean','i18n:nodes.SessionGateNode.allowed'),
        ('local_date','string','i18n:nodes.SessionGateNode.local_date'),
        ('session_date','string','i18n:nodes.SessionGateNode.session_date'),
        ('local_time','string','i18n:nodes.SessionGateNode.local_time'),
        ('reason','string','i18n:nodes.SessionGateNode.reason'),
    ]]
    _change_note: ClassVar[str] = 'Add immediate DST-aware and overnight session decisions.'
    _version: ClassVar[str] = '1.0.0'
    _updated_at: ClassVar[str] = '2026-09-20'
    _usage: ClassVar[dict[str,Any]] = {
        'when_to_use':['Check a market-local order window immediately before submission.','Handle overnight sessions, breaks and daylight-saving time.'],
        'when_not_to_use':['An authoritative exchange-open or holiday feed is required.','Wait until opening: use TradingHoursFilterNode.'],
        'typical_scenarios':['ScheduleNode -> SessionGateNode -> IfNode(allowed) -> strategy','Reservation -> SessionGateNode -> IfNode(allowed) -> OrderNode'],
    }
    _features: ClassVar[list[str]] = ['No credentials or network.','No sleeping and no dry-run bypass.','IANA timezone/DST and opening-weekday semantics.','Explicit IfNode controls downstream work.','Output is a pure function of the evaluation instant and the configuration (windows are start-inclusive and end-exclusive, plus days, closed_dates and the IANA timezone); replay evaluates it at the scenario as_of.','Two frames at the same instant produce the same allowed value; an outside-window scenario must sit at an instant outside the window.','allowed skips nothing by itself; bind it to an IfNode and hang the order chain on the IfNode true edge.']
    _anti_patterns: ClassVar[list[dict[str,str]]] = [{'pattern':'Connect directly to an order and assume an ordinary edge checks allowed.','reason':'Edges sequence execution; false output does not automatically skip successors.','alternative':'Bind allowed to IfNode and use its true edge.'}]
    _node_guide: ClassVar[dict[str,Any]] = {
        'input_handling':'Configure timezone, windows, days and optional closed_dates. No current-time override is accepted from workflow data.',
        'output_consumption':'Bind nodes.session.allowed to an explicit IfNode; local_date can anchor completed-bar calculations.',
        'common_combinations':['ScheduleNode, IfNode, CodeNode, SQLiteNode, OrderNode'],
        'pitfalls':['Refresh closed_dates or use an authoritative market-state source for holidays/halts.','Recheck near the order: earlier success does not stay valid indefinitely.','Independent workflows still require independent order guards.'],
    }
    _examples: ClassVar[list[dict[str, Any]]] = [
        {
            'title': label,
            'description': 'An explicit IfNode admits only the configured window. Add strategy nodes on its true port.',
            'expected_output': {'allowed': 'True inside the configured interval; false otherwise.'},
            'workflow_snippet': {
                'id': workflow_id, 'name': label, 'version': '1.0.0',
                'nodes': [
                    {'id': 'start', 'type': 'StartNode'},
                    {'id': 'session', 'type': 'SessionGateNode', 'timezone': zone,
                     'windows': windows, 'days': days, 'closed_dates': []},
                    {'id': 'allowed', 'type': 'IfNode', 'left': '{{ nodes.session.allowed }}',
                     'operator': '==', 'right': True},
                ],
                'edges': [{'from': 'start', 'to': 'session'}, {'from': 'session', 'to': 'allowed'}],
            },
        }
        for workflow_id, label, zone, windows, days in [
            ('session_day', 'Daytime window with DST', 'America/New_York',
             [{'start': '09:35', 'end': '15:50'}], ['mon', 'tue', 'wed', 'thu', 'fri']),
            ('session_overnight', 'Overnight opening weekday', 'Asia/Seoul',
             [{'start': '22:00', 'end': '05:00'}], ['fri']),
        ]
    ]

    @field_validator('timezone')
    @classmethod
    def valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('Unknown IANA timezone') from exc
        return value

    @field_validator('closed_dates')
    @classmethod
    def valid_dates(cls, values: list[str]) -> list[str]:
        for value in values:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError('Closed date must be YYYY-MM-DD')
        return values

    @classmethod
    def get_field_schema(cls):
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        descriptions={name:cls.model_fields[name].description for name in ('timezone','windows','days','closed_dates')}
        return {name:FieldSchema(name=name,type=kind,description=descriptions[name],required=name!='closed_dates',
                category=FieldCategory.PARAMETERS,expression_mode=ExpressionMode.FIXED_ONLY,
                **({'array_item_type':FieldType.OBJECT if name=='windows' else FieldType.STRING} if kind==FieldType.ARRAY else {}))
                for name,kind in [('timezone',FieldType.STRING),('windows',FieldType.ARRAY),('days',FieldType.ARRAY),('closed_dates',FieldType.ARRAY)]}

    def evaluate_at(self, instant: datetime) -> dict[str, Any]:
        """Pure time decision; the executable node always supplies the real clock."""
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError('Session clock must include timezone')
        local=instant.astimezone(ZoneInfo(self.timezone))
        current=local.hour*60+local.minute
        allowed_days={['mon','tue','wed','thu','fri','sat','sun'].index(day) for day in self.days}
        matched=None
        for window in self.windows:
            start=int(window.start[:2])*60+int(window.start[3:])
            end=int(window.end[:2])*60+int(window.end[3:])
            opening=local.date()-timedelta(days=1) if end<start and current<end else local.date()
            inside=start<=current<end if start<end else current>=start or current<end
            if inside and opening.weekday() in allowed_days and not {local.date().isoformat(),opening.isoformat()} & set(self.closed_dates):
                matched=opening.isoformat()
                break
        return {'allowed':matched is not None,'local_date':local.date().isoformat(),'session_date':matched or '',
                'local_time':local.isoformat(),'reason':'inside_configured_window' if matched else 'outside_configured_window'}

    async def execute(self, context: Any) -> dict[str, Any]:
        return self.evaluate_at(datetime.now(timezone.utc))
