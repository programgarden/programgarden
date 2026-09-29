"""Session boundaries, overnight weekday ownership, DST and fail-closed config."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from programgarden_core import SessionGateNode, NodeTypeRegistry


def gate(**kwargs):
    return SessionGateNode(id='session',timezone='America/New_York',windows=[{'start':'09:35','end':'15:50'}],days=['mon','tue','wed','thu','fri'],**kwargs)


@pytest.mark.parametrize('instant,allowed',[
 ('2026-01-05T14:34:59+00:00',False),('2026-01-05T14:35:00+00:00',True),
 ('2026-01-05T20:49:59+00:00',True),('2026-01-05T20:50:00+00:00',False),
 ('2026-07-06T13:35:00+00:00',True),('2026-07-06T19:50:00+00:00',False),
 ('2026-07-04T14:00:00+00:00',False),
])
def test_window_and_dst(instant,allowed):
    assert gate().evaluate_at(datetime.fromisoformat(instant))['allowed'] is allowed


def test_overnight_uses_opening_weekday_and_exclusions():
    node=SessionGateNode(id='s',timezone='Asia/Seoul',windows=[{'start':'22:00','end':'05:00'}],days=['fri'])
    assert node.evaluate_at(datetime.fromisoformat('2026-09-19T04:00:00+09:00'))['session_date']=='2026-09-18'
    assert not node.evaluate_at(datetime.fromisoformat('2026-09-19T05:00:00+09:00'))['allowed']
    assert not node.evaluate_at(datetime.fromisoformat('2026-09-18T04:00:00+09:00'))['allowed']
    for closed in ['2026-09-18','2026-09-19']:
        node.closed_dates=[closed]
        assert not node.evaluate_at(datetime.fromisoformat('2026-09-19T04:00:00+09:00'))['allowed']


def test_break_and_fall_back_hour():
    node=SessionGateNode(id='s',timezone='America/New_York',windows=[{'start':'00:00','end':'02:00'},{'start':'03:00','end':'04:00'}],days=['sun'])
    for instant in ['2026-11-01T05:30:00+00:00','2026-11-01T06:30:00+00:00']:
        assert node.evaluate_at(datetime.fromisoformat(instant))['allowed']
    assert not node.evaluate_at(datetime.fromisoformat('2026-11-01T07:30:00+00:00'))['allowed']


@pytest.mark.parametrize('changed',[{'timezone':'Missing/Zone'},{'windows':[]},{'windows':[{'start':'25:00','end':'16:00'}]}, {'windows':[{'start':'09:30','end':'09:30'}]}, {'windows':[{'start':'9:30','end':'16:00'}]}, {'days':['unknown']},{'days':[]},{'closed_dates':['20260920']}])
def test_bad_configuration_never_passes(changed):
    args={'id':'s','timezone':'UTC','windows':[{'start':'09:00','end':'16:00'}],'days':['mon']}
    with pytest.raises(ValidationError):SessionGateNode(**(args|changed))


@pytest.mark.asyncio
async def test_dry_run_uses_same_gate_and_registry_exposes_contract():
    node=gate()
    with patch('programgarden_core.nodes.session_gate.datetime') as clock:
        clock.now.return_value=datetime.fromisoformat('2026-09-20T12:00:00+00:00')
        result=await node.execute(SimpleNamespace(is_dry_run=True))
    assert not result['allowed']
    schema=NodeTypeRegistry().get_schema('SessionGateNode')
    assert set(schema.config_schema)=={'timezone','windows','days','closed_dates','exchange_calendar'}
    assert {'allowed','local_date','session_date','local_time','reason'}=={p['name'] for p in schema.outputs}
    with pytest.raises(ValueError):node.evaluate_at(datetime(2026,1,1))


@pytest.mark.parametrize('calendar', ['XNYS', 'XNAS'])
@pytest.mark.parametrize('instant,allowed', [
    ('2026-12-25T11:00:00-05:00', False),
    ('2026-11-27T14:00:00-05:00', False),
    ('2026-11-27T12:59:59-05:00', True),
    ('2026-11-27T13:00:00-05:00', False),
    ('2026-12-24T13:00:00-05:00', False),
    ('2026-07-03T11:00:00-04:00', False),
    ('2026-07-02T14:00:00-04:00', True),
    ('2026-06-19T11:00:00-04:00', False),
    ('2026-04-03T11:00:00-04:00', False),
    ('2026-11-11T11:00:00-05:00', True),
    ('2026-10-12T11:00:00-04:00', True),
    ('2026-03-09T13:35:00Z', True),
    ('2026-11-02T14:35:00Z', True),
    ('2025-01-09T11:00:00-05:00', False),
    ('2027-12-24T11:00:00-05:00', False),
])
def test_published_us_equity_calendar(calendar, instant, allowed):
    # Exchange calendars, not the broader federal/bond holiday calendar.
    assert gate(exchange_calendar=calendar).evaluate_at(datetime.fromisoformat(instant))['allowed'] is allowed


def test_calendar_is_opt_in_and_cannot_widen_the_user_window():
    holiday = datetime.fromisoformat('2026-12-25T11:00:00-05:00')
    assert gate().evaluate_at(holiday)['allowed'] is True
    node = gate(exchange_calendar='XNAS', closed_dates=['2026-09-29'])
    assert node.evaluate_at(datetime.fromisoformat('2026-09-29T11:00:00-04:00'))['allowed'] is False
    assert node.evaluate_at(datetime.fromisoformat('2026-09-30T09:32:00-04:00'))['allowed'] is False


def test_calendar_failure_blocks_instead_of_falling_back_to_weekdays():
    with patch('programgarden_core.market_calendar.scheduled_session_open', side_effect=ImportError('missing dependency')):
        result = gate(exchange_calendar='XNAS').evaluate_at(datetime.fromisoformat('2026-09-29T11:00:00-04:00'))
    assert result['allowed'] is False
    assert result['reason'] == 'calendar_unavailable'
    assert result['session_date'] == ''


def test_calendar_contract_rejects_unimplemented_markets_and_is_discoverable():
    with pytest.raises(ValidationError):
        gate(exchange_calendar='KRX')
    field = SessionGateNode.get_field_schema()['exchange_calendar']
    assert field.required is False
    assert field.enum_values == ['XNYS', 'XNAS']
