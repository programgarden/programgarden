"""Native detail metadata never invents expiry, margin, quote or account evidence."""
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden_core import NodeTypeRegistry, OverseasFuturesContractInfoNode
from programgarden.executor import FuturesContractInfoNodeExecutor
from programgarden.futures_contract_info import (
    DATE_FIELDS, NUMBER_FIELDS, TEXT_FIELDS, TIME_FIELDS,
    build_contract_info_request, read_contract_info,
)
from programgarden_finance.ls.overseas_futureoption.market.o3105.blocks import O3105OutBlock, O3105Response
from programgarden.validation_replay import replay
from tests.test_futures_orderable_evidence import config as capacity_config, execution_context
from tests.test_replay_sources import futures_case

NOW = datetime(2026, 10, 20, 6, 30, tzinfo=UTC)


def config():
    return {"symbol": {"symbol": "HMHU26", "exchange": "HKEX"}, "connection": capacity_config()["connection"]}


def source(**changes):
    return {"status_code": 200, "rsp_cd": "00000", "rsp_msg": "OK", "block": {
        "Symbol": "HMHU26", "ExchCd": "HKEX", "SymbolNm": "Recorded mini futures", "BscGdsCd": "HMH",
        "CrncyCd": "HKD", "MtrtDt": "20260930", "FnlDlDt": "20260929", "FstTrsfrDt": "",
        "ApplDate": "20260922", "OpngMgn": 12000.0, "MntncMgn": 9500.0,
        "UntPrc": 1.0, "MnChgAmt": 10.0, "DlDt": "20260922", "DlStrtTm": "101500", "DlEndTm": "173000",
        "OvsStrDay": "20260922", "OvsStrTm": "091500", "OvsEndDay": "20260922", "OvsEndTm": "163000",
        **changes,
    }}


def parse(raw=None):
    return read_contract_info(O3105Response.model_validate(raw or source()), config(), observed_at=NOW)


def test_sdk_field_contract_and_declared_outputs_cover_every_emitted_field():
    consumed = {"Symbol", "ExchCd"} | set(TEXT_FIELDS.values()) | set(DATE_FIELDS.values()) | set(TIME_FIELDS.values()) | set(NUMBER_FIELDS.values())
    assert consumed <= O3105OutBlock.model_fields.keys()
    assert build_contract_info_request(config()).model_dump() == {"symbol": "HMHU26"}
    schema = NodeTypeRegistry().get_schema("OverseasFuturesContractInfoNode")
    assert schema.product_scope == "overseas_futures"
    assert {p['name'] for p in schema.outputs} == {"value", "verified", "missing_fields", "error"}
    fields = next(p for p in schema.outputs if p['name'] == "value")['fields']
    assert {f['name'] for f in fields} == set(parse()['value'])
    assert OverseasFuturesContractInfoNode.is_tool_enabled()


@pytest.mark.parametrize('quote', [None, 0.0, -1.0])
def test_static_details_do_not_require_a_current_positive_quote(quote):
    raw = source()
    if quote is not None:
        raw['block']['TrdP'] = quote
    result = parse(raw)
    assert result['verified'] and result['error'] is None
    assert result['value']['maturity_date'] == '2026-09-30'
    assert result['value']['last_trading_date'] == '2026-09-29'
    assert result['value']['initial_margin'] == 12000
    assert result['value']['korea_start_time'] == '10:15:00'
    assert result['value']['observed_at'] == NOW.isoformat()


@pytest.mark.parametrize('field', list(DATE_FIELDS.values()) + list(TIME_FIELDS.values()))
@pytest.mark.parametrize('value', ['', '00000000', '20260230', '246060', '2026-09-29'])
def test_invalid_dates_and_times_stay_unknown(field, value):
    # Some malformed time inputs have a valid date length; the date/time distinction remains strict.
    result = parse(source(**{field: value}))
    name = next(k for k, v in {**DATE_FIELDS, **TIME_FIELDS}.items() if v == field)
    assert result['value'][name] is None
    assert name in result['missing_fields']


def test_sdk_defaults_are_not_treated_as_observations():
    result = parse({'status_code': 200, 'rsp_cd': '00000', 'rsp_msg': 'OK', 'block': {'Symbol': 'HMHU26', 'ExchCd': 'HKEX'}})
    assert result['verified']
    for name in list(DATE_FIELDS) + list(TIME_FIELDS) + list(NUMBER_FIELDS) + list(TEXT_FIELDS):
        assert result['value'][name] is None
        assert name in result['missing_fields']


@pytest.mark.parametrize('value', [-1.0, float('nan'), float('inf')])
def test_invalid_margin_remains_unknown(value):
    assert parse(source(OpngMgn=value))['value']['initial_margin'] is None


def test_explicit_zero_margin_is_distinct_from_missing_but_zero_tick_is_unavailable():
    result = parse(source(OpngMgn=0.0, UntPrc=0.0))
    assert result['value']['initial_margin'] == 0
    assert result['value']['tick_size'] is None


@pytest.mark.parametrize('change', ['http', 'rsp', 'error', 'missing', 'symbol', 'exchange', 'missing_symbol'])
def test_failed_or_wrong_contract_response_never_becomes_verified(change):
    raw = source()
    if change == 'http': raw['status_code'] = 500
    elif change == 'rsp': raw['rsp_cd'] = '00136'
    elif change == 'error': raw['error_msg'] = 'PRIVATE TOKEN'
    elif change == 'missing': raw['block'] = None
    elif change == 'symbol': raw['block']['Symbol'] = 'HMHZ26'
    elif change == 'exchange': raw['block']['ExchCd'] = 'CME'
    elif change == 'missing_symbol': del raw['block']['Symbol']
    with pytest.raises(ValueError) as failure:
        parse(raw)
    assert 'PRIVATE' not in str(failure.value)


@pytest.mark.asyncio
async def test_live_executor_uses_only_the_selected_broker_and_one_read():
    api = MagicMock()
    call = api.overseas_futureoption.return_value.market.return_value.o3105.return_value
    call.req_async = AsyncMock(return_value=O3105Response.model_validate(source()))
    with patch('programgarden.executor.ensure_ls_login', return_value=(api, True, None)) as login:
        result = await FuturesContractInfoNodeExecutor().execute('detail', 'OverseasFuturesContractInfoNode', config(), execution_context())
    assert result['verified']
    assert login.call_args.args[:2] == ('selected-key', 'selected-secret')
    call.req_async.assert_awaited_once()
    api.overseas_futureoption.return_value.accno.assert_not_called()
    api.overseas_futureoption.return_value.order.assert_not_called()


@pytest.mark.asyncio
async def test_missing_credential_cannot_fall_back_to_another_account():
    with patch('programgarden.executor.ensure_ls_login') as login:
        result = await FuturesContractInfoNodeExecutor().execute('detail', 'OverseasFuturesContractInfoNode', config(), execution_context('missing'))
    login.assert_not_called()
    assert not result['verified'] and result['value'] is None


@pytest.mark.asyncio
async def test_deep_validation_is_network_free_and_does_not_invent_dates():
    context = MagicMock(is_deep_validate=True)
    context.get_deep_fixture.return_value = None
    with patch('programgarden.executor.evaluate_all_bindings', side_effect=lambda c, *_: c), patch('programgarden.executor.ensure_ls_login') as login:
        result = await FuturesContractInfoNodeExecutor().execute('detail', 'OverseasFuturesContractInfoNode', config(), context)
    login.assert_not_called()
    assert result['value']['last_trading_date'] is None


@pytest.mark.asyncio
async def test_replay_runs_native_parser_and_rejects_mismatched_recordings():
    node = {'id': 'detail', 'type': 'OverseasFuturesContractInfoNode', 'symbol': config()['symbol']}
    graph, fixture = futures_case(node, source())
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs['detail']['value']['last_trading_date'] == '2026-09-29'
    assert result.outputs['detail']['value']['observed_at'] == '2026-09-22T14:00:00+00:00'
    bad = deepcopy(fixture)
    bad['nodes']['detail']['source']['block']['Symbol'] = 'HMHZ26'
    assert not (await replay(graph, bad)).passed


@pytest.mark.asyncio
async def test_futures_fill_stream_uses_selected_credential_and_refuses_cross_account_reuse():
    from programgarden.executor import RealOrderEventNodeExecutor
    executor = RealOrderEventNodeExecutor()
    context = execution_context()
    with patch('programgarden.executor.ensure_ls_login', return_value=(MagicMock(), True, None)) as login, \
         patch.object(executor, '_ls_futures_order_event', new=AsyncMock(return_value={'status':'subscribed'})):
        assert (await executor._execute_ls('events','overseas_futures',config(),context,True))['status']=='subscribed'
        assert login.call_args.args[:3] == ('selected-key','selected-secret',True)
        login.reset_mock()
        context._futures_order_event_owner=('other-broker','other-credential',True)
        result=await executor._execute_ls('events','overseas_futures',config(),context,True)
        assert result.get('error')
        login.assert_not_called()


def test_native_fill_identity_fields_exist_in_sdk_and_catalog():
    from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import TC3RealResponseBody
    assert {'svc_id','ordr_no','ordr_dt','is_cd','s_b_ccd','ccls_q','ccls_prc','ccls_no','ccls_tm'} <= TC3RealResponseBody.model_fields.keys()
    schema=NodeTypeRegistry().get_schema('OverseasFuturesRealOrderEventNode')
    fields=next(p for p in schema.outputs if p['name']=='filled')['fields']
    assert {'tr_cd','svc_id','order_date','fill_no','filled_quantity'} <= {f['name'] for f in fields}
