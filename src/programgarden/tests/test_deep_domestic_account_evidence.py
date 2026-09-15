"""Virtual account observations must satisfy the same entry contract as runtime."""
import socket
from unittest.mock import patch

import pytest
from programgarden import ProgramGarden
from programgarden.deep_fixtures import account_fixture


GUARD = """async def execute(data, params, context):
    if not isinstance(data, list):
        raise ValueError('Missing held-symbol evidence')
    for row in data:
        if not isinstance(row, dict) or row.get('exchange') != 'KRX' or len(row.get('symbol', '')) != 6:
            raise ValueError('Malformed domestic holding')
    if params.get('partial') or params.get('order_error'):
        raise ValueError('Incomplete account or pending read')
    if not isinstance(params.get('orders'), list):
        raise ValueError('Missing pending orders')
    if data:
        return {'symbols': []}
    quotes = params.get('quotes')
    matches = [q for q in quotes if q.get('symbol') == '005930' and q.get('exchange') == 'KRX']
    if len(matches) != 1 or matches[0]['price'] <= 0:
        raise ValueError('Missing matching quote')
    if params['balance']['orderable_amount'] < matches[0]['price']:
        return {'symbols': []}
    return {'symbols': matches}
"""


def workflow():
    nodes = [
        {'id':'start','type':'StartNode'},
        {'id':'broker','type':'KoreaStockBrokerNode','credential_id':'test'},
        {'id':'account','type':'KoreaStockAccountNode'},
        {'id':'pending','type':'KoreaStockOpenOrdersNode'},
        {'id':'quotes','type':'KoreaStockMarketDataNode','symbols':[{'symbol':'005930','exchange':'KRX'}]},
        {'id':'guard','type':'CodeNode','data':'{{ nodes.account.held_symbols }}',
         'params':{'balance':'{{ nodes.account.balance }}', 'partial':'{{ nodes.account.balance._partial_failure }}',
                   'orders':'{{ nodes.pending.open_orders }}','order_error':"{{ nodes.pending['error'] }}",
                   'quotes':'{{ nodes.quotes.values }}'},
         'code':GUARD,'outputs':[{'name':'symbols','type':'array'}]},
        {'id':'sizing','type':'PositionSizingNode','method':'fixed_quantity','fixed_quantity':1,
         'symbols':'{{ nodes.guard.symbols }}','balance':'{{ nodes.account.balance }}'},
        {'id':'buy','type':'KoreaStockNewOrderNode','side':'buy','order_type':'limit','order':'{{ nodes.sizing.order }}'},
    ]
    return {'id':'domestic-fixture-regression','name':'Domestic fixture regression','nodes':nodes,
            'edges':[{'from':a['id'],'to':b['id']} for a,b in zip(nodes,nodes[1:])],
            'credentials':[{'credential_id':'test','type':'broker_ls_korea_stock','data':[]}]}


@pytest.mark.parametrize('fixtures,expected', [
    (None,True),
    ({'account':{'positions':[],'held_symbols':[]}},True),
    ({'account':{'held_symbols':None}},False),
    ({'account':{'held_symbols':[{'symbol':'AAPL','exchange':'NASDAQ'}]}},False),
    ({'pending':{'error':'Read failed'}},False),
])
def test_virtual_entry_checks_preserve_complete_and_incomplete_evidence(fixtures,expected):
    with patch.object(socket.socket,'connect',side_effect=AssertionError('No network in deep validation')), \
         patch('programgarden.executor.ensure_ls_login',side_effect=AssertionError('No broker login')):
        result=ProgramGarden().validate_deep(workflow(),fixtures=fixtures,timeout=15)
    assert result.is_valid is expected, [e.model_dump() for e in result.errors]


@pytest.mark.parametrize('symbols', [['001500'], {'symbol':'001500'}, '001500'])
def test_domestic_fixture_preserves_requested_symbols_and_currency(symbols):
    result=account_fixture({'symbols':symbols},product='korea_stock')
    assert result['held_symbols']==[{'symbol':'001500','exchange':'KRX'}]
    assert result['positions'][0]['currency']=='KRW'
    assert 'KRW' in result['balance'] and 'USD' not in result['balance']
    assert result['balance']['_partial_failure'] is False


def test_foreign_fixture_keeps_its_existing_identity_and_currency():
    result=account_fixture({})
    assert result['held_symbols']==[{'symbol':'AAPL','exchange':'NASDAQ'}]
    assert result['positions'][0]['currency']=='USD'
