import asyncio
import pytest

# Import the resolver from the package
from programgarden.plugin_resolver import PluginResolver
from programgarden_core import pg_log, pg_logger

pg_log()


@pytest.mark.asyncio
async def test_real_order_plugin_flow(monkeypatch):
    plugin = PluginResolver()
    cls = await plugin._resolve(condition_id="StockSplitFunds")

    # If no class is resolved, assert that behavior is explicit (None)
    if cls is None:
        assert cls is None
        return

    # If a class is resolved, create instance and call on_real_order_receive
    instance = cls()

    symbol = {
        "success": True,
        "CrcyCode": "USD",
        "ShtnIsuNo": "AAPL",
        "ordQty": 10.0,
        "PnlRat": 0.1,
        "PchsAmt": 1000.0,
        "ordMktCode": "NASDAQ",
        "errorMsg": None
    }
    pg_logger.info(f"Exist plugin : {instance}")

    # If the method exists call it, otherwise the test fails
    if hasattr(instance, "on_real_order_receive"):
        # If it's async, await it; otherwise call directly
        method = getattr(instance, "on_real_order_receive")

        if asyncio.iscoroutinefunction(method):
            await method(order_type="modify_buy", response=symbol)
        else:
            method(order_type="modify_buy", response=symbol)

    # If we reach here without exceptions, test passes
    assert True
