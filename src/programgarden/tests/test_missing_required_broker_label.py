"""MISSING_REQUIRED_BROKER must name the broker node of the *node's own* product scope.

Regression for programgarden <= 2.4.0, where every non-``overseas_stock`` scope was
labelled ``overseas_futures`` / ``OverseasFuturesBrokerNode`` — a ``KoreaStockAccountNode``
without a broker was told to add an overseas-futures broker, and the AI authoring loop
followed that advice (dev smoke, 2026-09-27).
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from programgarden import WorkflowExecutor
from programgarden_core import ErrorCode


def _wrap(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": "test-wf",
        "name": "missing broker label test",
        "version": "1.0",
        "nodes": nodes,
        "edges": edges,
        "credentials": [],
    }


def _code(err) -> str:
    return err.code if isinstance(err.code, str) else err.code.value


@pytest.mark.parametrize(
    ("node_type", "scope", "broker_node"),
    [
        ("KoreaStockAccountNode", "korea_stock", "KoreaStockBrokerNode"),
        ("OverseasStockAccountNode", "overseas_stock", "OverseasStockBrokerNode"),
        ("OverseasFuturesAccountNode", "overseas_futures", "OverseasFuturesBrokerNode"),
    ],
)
def test_missing_required_broker_names_the_scope_broker(
    node_type: str, scope: str, broker_node: str
) -> None:
    executor = WorkflowExecutor()
    workflow = _wrap(
        [
            {"id": "start", "type": "StartNode"},
            {"id": "acct", "type": node_type},
        ],
        [{"from": "start", "to": "acct"}],
    )
    result = executor.validate(workflow)

    missing = [e for e in result.errors if _code(e) == ErrorCode.MISSING_REQUIRED_BROKER.value]
    assert missing, f"expected MISSING_REQUIRED_BROKER for {node_type}, got {[_code(e) for e in result.errors]}"
    err = missing[0]

    assert err.details["product_scope"] == scope
    assert err.details["expected_broker_node"] == broker_node
    assert f"requires a {scope} broker" in err.message
    assert broker_node in (err.suggestion or "")

    # The old bug: every non-stock scope pointed at the overseas-futures broker.
    if scope != "overseas_futures":
        assert "OverseasFuturesBrokerNode" not in (err.suggestion or "")
        assert "overseas_futures" not in err.message
