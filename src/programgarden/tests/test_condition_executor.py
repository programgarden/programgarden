import pytest

from programgarden.condition_executor import ConditionExecutor


class DummyResolver:
    async def get_order_types(self, _condition_id):
        return None

    async def resolve_condition(self, *_args, **_kwargs):
        return None

    def reset_error_tracking(self):
        return None


class DummySymbolProvider:
    async def get_symbols(self, *args, **kwargs):
        return []


@pytest.mark.asyncio
async def test_execute_condition_list_coerces_futures_symbols():
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    system = {
        "settings": {"system_id": "sys-1"},
        "securities": {"product": "overseas_futures"},
    }

    strategy = {
        "id": "strat-1",
        "logic": "and",
        "conditions": [],
        "symbols": [
            {
                "symbol": "ADZ25",
                "exchange": "CME",
                "name": "Australian Dollar",
            }
        ],
    }

    result = await executor.execute_condition_list(system=system, strategy=strategy)

    assert result[0]["product_type"] == "overseas_futures"
    assert result[0]["exchcd"] == "CME"
    assert result[0]["symbol_name"] == "Australian Dollar"
    assert result[0]["position_side"] == "flat"


@pytest.mark.asyncio
async def test_execute_condition_list_coerces_stock_symbols():
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    system = {
        "settings": {"system_id": "sys-2"},
        "securities": {"product": "overseas_stock"},
    }

    strategy = {
        "id": "strat-2",
        "logic": "and",
        "conditions": [],
        "symbols": [
            {
                "symbol": "AAPL",
                "exchange": "NYSE",
                "name": "Apple Inc.",
            }
        ],
    }

    result = await executor.execute_condition_list(system=system, strategy=strategy)

    assert result[0]["product_type"] == "overseas_stock"
    assert result[0]["exchcd"] == "81"
    assert result[0]["symbol_name"] == "Apple Inc."
    assert "position_side" not in result[0]


@pytest.mark.asyncio
async def test_execute_condition_list_coerces_stock_symbols_alias_amex():
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    system = {
        "settings": {"system_id": "sys-2"},
        "securities": {"product": "overseas_stock"},
    }

    strategy = {
        "id": "strat-3",
        "logic": "and",
        "conditions": [],
        "symbols": [
            {
                "symbol": "XYZ",
                "exchange": "AMEX",
            }
        ],
    }

    result = await executor.execute_condition_list(system=system, strategy=strategy)

    assert result[0]["exchcd"] == "81"
