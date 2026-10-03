"""Long offline timelines preserve every cron instant and the same SQLite state."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_events import checked_events
from programgarden.replay_scenarios import check_final_expectations
from programgarden.validation_replay import replay
from tests.test_replay_events import counter


def timeline():
    graph, fixture = counter()
    graph['nodes'][1]['cron'] = '0 * * * *'
    initial = datetime.fromisoformat(fixture['as_of'].replace('Z', '+00:00'))
    fixture['events'] = []
    for hour in range(1, 49):
        expected = deepcopy(fixture['expected'])
        expected['count']['properties']['rows']['const'] = [{'count': hour + 1}]
        fixture['events'].append({
            'as_of': (initial + timedelta(hours=hour)).isoformat(),
            'type': 'schedule_tick', 'source_node_id': 'schedule',
            'expected': expected, 'must_execute': ['append', 'count'],
        })
    return graph, fixture


@pytest.mark.asyncio
async def test_two_days_preserve_state_without_changing_interactive_limit():
    graph, fixture = timeline()
    limited = await replay(graph, fixture)
    assert not limited.passed and not limited.executed
    for _ in range(2):
        result = await replay(graph, fixture, event_limit=48)
        assert result.passed, result.errors
        check_final_expectations(result, fixture, graph, event_limit=48)
        assert len(result.events) == 48
        assert result.initial_outputs['count']['rows'] == [{'count': 1}]
        assert result.events[-1]['outputs']['count']['rows'] == [{'count': 49}]
        with pytest.raises(ContractViolation):
            check_final_expectations(result, fixture, graph)


@pytest.mark.asyncio
async def test_extended_timeline_still_rejects_a_skipped_cron_tick():
    graph, fixture = timeline()
    fixture['events'].pop(24)
    result = await replay(graph, fixture, event_limit=48)
    assert not result.passed
    assert any('next configured cron instant' in e.get('message', '') for e in result.errors)


@pytest.mark.asyncio
async def test_correct_final_count_cannot_hide_an_incorrect_intermediate_count():
    graph, fixture = timeline()
    result = await replay(graph, fixture, event_limit=48)
    assert result.passed
    fixture['events'][24]['expected']['count']['properties']['rows']['const'] = [{'count': 1}]
    with pytest.raises(ContractViolation):
        check_final_expectations(result, fixture, graph, event_limit=48)


@pytest.mark.parametrize('limit', [-1, True, None, 4097, 48.0, '48'])
def test_event_budget_requires_a_bounded_explicit_integer(limit):
    with pytest.raises(ContractViolation):
        checked_events({}, event_limit=limit)


def test_fixture_cannot_raise_its_own_event_budget():
    _, fixture = timeline()
    fixture['event_limit'] = 4096
    with pytest.raises(ContractViolation):
        checked_events(fixture)
