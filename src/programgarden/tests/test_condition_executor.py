"""ConditionExecutor 테스트 모듈.

해외선물 position_side 처리 로직 테스트:
- long/short: 방향 결정 조건, 모든 방향 조건이 동일해야 성공
- neutral: 방향 결정에 관여하지 않음, 다른 조건에 위임
- flat: 하나라도 있으면 전체 실패
- 해외주식: position_side 무시, success만 사용
"""
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


@pytest.mark.asyncio
async def test_evaluate_logic_futures_all_long():
    """All futures conditions return long -> success with long direction."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "long", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "long", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is True
    assert side == "long"


@pytest.mark.asyncio
async def test_evaluate_logic_futures_mixed_directions():
    """Mixed long/short directions -> failure."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "long", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "short", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is False
    assert side is None


@pytest.mark.asyncio
async def test_evaluate_logic_futures_with_neutral():
    """Neutral conditions delegate direction to others."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "long", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "neutral", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "neutral", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is True
    assert side == "long"


@pytest.mark.asyncio
async def test_evaluate_logic_futures_all_neutral():
    """All neutral conditions -> failure (no direction determined)."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "neutral", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "neutral", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is False
    assert side is None


@pytest.mark.asyncio
async def test_evaluate_logic_futures_flat_causes_failure():
    """Any flat condition causes overall failure."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "long", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "flat", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is False
    assert side is None


@pytest.mark.asyncio
async def test_evaluate_logic_futures_neutral_with_short():
    """Neutral + short -> success with short direction."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_futures", "position_side": "short", "weight": 1},
        {"success": True, "product": "overseas_futures", "position_side": "neutral", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is True
    assert side == "short"


@pytest.mark.asyncio
async def test_evaluate_logic_stock_only_ignores_futures_alignment():
    """Stock-only conditions should not trigger futures direction checks."""
    executor = ConditionExecutor(resolver=DummyResolver(), symbol_provider=DummySymbolProvider())

    results = [
        {"success": True, "product": "overseas_stock", "weight": 1},
        {"success": True, "product": "overseas_stock", "weight": 1},
    ]

    success, weight, side = executor.evaluate_logic(results, logic="and")

    assert success is True
    assert side is None