"""A recording's ports apply in the declared order, so replay iterates like the live executor,
and an unknown request field is named."""
import pytest

from programgarden.replay_contracts import ContractViolation
from programgarden.replay_external import recording, request_identity
from programgarden.validation_replay import replay

AS_OF = "2026-09-22T14:00:00Z"
CONNECTION = {"product": "overseas_stock"}
AAPL = {"symbol": "AAPL", "exchange": "NASDAQ"}


def test_unknown_request_fields_are_named_with_the_accepted_ones():
    """dev 5d9961de (2026-09-25): a builder wrote `fields: ["price"]` on a market-data node and
    retried the same config twice on the bare "Unknown recording request fields"."""
    with pytest.raises(ContractViolation) as caught:
        request_identity("OverseasStockMarketDataNode", {"symbols": [AAPL], "fields": ["price"]})
    message = str(caught.value)
    assert "Unknown recording request fields: fields" in message and "accepts:" in message and "symbols" in message


@pytest.mark.asyncio
async def test_recorded_port_order_does_not_change_auto_iteration():
    """dev 5d9961de (2026-09-25): the suite recorded open_orders as {"count": 1, "open_orders": [...]}
    while the live executor returns {"open_orders": [...], "count": 1}. The auto-iteration
    fallback source is a node's FIRST output, so replay read `count` (no iteration) where live
    reads the non-empty list (iterates) and the per-item quote recording was "not required"."""
    row = {"order_id": "O1", "symbol": "AAPL", "exchange": "NASDAQ", "side": "buy", "quantity": 1,
           "remaining_quantity": 1, "price": 90.0, "status": "open"}
    definition = {"id": "w", "name": "order of ports", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        {"id": "orders", "type": "OverseasStockOpenOrdersNode"},
        {"id": "quote", "type": "OverseasStockMarketDataNode", "symbols": [AAPL]},
    ], "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "orders"}, {"from": "orders", "to": "quote"}]}
    fixture = {"as_of": AS_OF, "nodes": {
        "broker": recording("OverseasStockBrokerNode", {}, {"connection": CONNECTION},
                            {"type": "object", "required": ["connection"]}, as_of=AS_OF),
        # count FIRST on purpose: the designer's order, not the executor's
        "orders": recording("OverseasStockOpenOrdersNode", {"connection": CONNECTION},
                            {"count": 1, "open_orders": [row]},
                            {"type": "object", "required": ["open_orders", "count"]}, as_of=AS_OF),
        "quote": {"items": {"NASDAQ:AAPL": recording("OverseasStockMarketDataNode",
                            {"symbols": [AAPL], "connection": CONNECTION},
                            {"values": [{**AAPL, "price": 100.0}]},
                            {"type": "object", "required": ["values"]}, as_of=AS_OF, item=row)}},
    }}  # the iteration item IS the open-order row the quote node runs for
    result = await replay(definition, fixture)
    assert result.passed, result.errors
    assert result.executed == ["start", "broker", "orders", "quote"]
    assert result.outputs["quote"]["values"][0]["price"] == 100.0
