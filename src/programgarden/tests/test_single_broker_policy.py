"""The account policy must reject invalid graphs before any broker login."""
from itertools import product
from unittest.mock import patch

import pytest

from programgarden import ProgramGarden
from programgarden_core import WorkflowDefinition
from programgarden_core.models.workflow import validate_broker_connections

BROKERS = ("OverseasStockBrokerNode", "OverseasFuturesBrokerNode", "KoreaStockBrokerNode")


def definition(*brokers, credential=None):
    nodes = [{"id": "start", "type": "StartNode"}]
    nodes += [{"id": f"broker_{i}", "type": kind, **({"credential_id": credential} if credential else {})} for i, kind in enumerate(brokers)]
    return {"id": "broker-policy-fixture", "name": "Broker policy fixture", "nodes": nodes, "edges": [{"from": "start", "to": n["id"]} for n in nodes[1:]]}


@pytest.mark.parametrize("brokers", [(), *[(kind,) for kind in BROKERS]])
def test_no_account_requirement_and_one_broker_remain_valid(brokers):
    workflow = definition(*brokers)
    assert validate_broker_connections(workflow["nodes"]) == []
    assert not WorkflowDefinition(**workflow).validate_structure()
    result = ProgramGarden().validate(workflow)
    assert result.is_valid, result.errors


@pytest.mark.parametrize("brokers", list(product(BROKERS, repeat=2)))
@pytest.mark.parametrize("credential", [None, "shared-credential-reference"])
def test_every_pair_is_rejected_even_unbound_or_sharing_credentials(brokers, credential):
    workflow = definition(*brokers, credential=credential)
    errors = validate_broker_connections(workflow["nodes"])
    assert len(errors) == 1
    error = errors[0]
    assert error.code == "DUPLICATE_BROKER_NODE"
    assert error.location.node_id == "broker_1"
    assert error.details["broker_node_ids"] == ["broker_0", "broker_1"]
    assert "separate workflow" in error.suggestion
    result = ProgramGarden().validate(workflow)
    assert not result.is_valid
    assert sum(e.code == "DUPLICATE_BROKER_NODE" for e in result.errors) == 1


def test_three_products_report_both_additional_brokers():
    errors = validate_broker_connections(definition(*BROKERS)["nodes"])
    assert [e.location.node_id for e in errors] == ["broker_1", "broker_2"]


def test_one_connection_fans_out_without_counting_unrelated_credentials():
    workflow = definition("KoreaStockBrokerNode")
    workflow["nodes"] += [{"id": "left", "type": "ThrottleNode"}, {"id": "right", "type": "ThrottleNode"}]
    workflow["edges"] += [{"from": "broker_0", "to": side} for side in ("left", "right")]
    workflow["credentials"] = [{"credential_id": "llm-credential", "type": "llm", "data": []}]
    assert not WorkflowDefinition(**workflow).validate_structure()


def test_deep_validation_blocks_before_broker_login():
    with patch("programgarden_finance.LS.login", side_effect=AssertionError("Broker login must not occur")) as login:
        result = ProgramGarden().validate_deep(definition(*BROKERS[:2]))
    assert not result.is_valid
    assert any(e.code == "DUPLICATE_BROKER_NODE" for e in result.errors)
    login.assert_not_called()


def test_sync_run_blocks_before_broker_login(tmp_path):
    with patch("programgarden_finance.LS.login", side_effect=AssertionError("Broker login must not occur")) as login:
        with pytest.raises(ValueError, match="Duplicate broker connection"):
            ProgramGarden().run(definition(*BROKERS[:2]), storage_dir=str(tmp_path))
    login.assert_not_called()


@pytest.mark.asyncio
async def test_async_run_blocks_before_broker_login(tmp_path):
    with patch("programgarden_finance.LS.login", side_effect=AssertionError("Broker login must not occur")) as login:
        with pytest.raises(ValueError, match="Duplicate broker connection"):
            await ProgramGarden().run_async(definition(*BROKERS[:2]), storage_dir=str(tmp_path))
    login.assert_not_called()


def test_compile_cannot_produce_executable_objects_for_multiple_connections():
    from programgarden import WorkflowExecutor

    resolved, result = WorkflowExecutor().compile(definition(*BROKERS[:2]))
    assert resolved is None
    assert not result.is_valid
    assert any(error.code == "DUPLICATE_BROKER_NODE" for error in result.errors)


def test_registered_connection_output_counts_custom_brokers(monkeypatch):
    from programgarden_core.registry import NodeTypeRegistry

    registry = NodeTypeRegistry()
    builtin_schema = registry.get_schema("KoreaStockBrokerNode")
    monkeypatch.setitem(registry._schemas, "CustomBroker", builtin_schema.model_copy(update={"node_type": "CustomBroker"}))
    errors = validate_broker_connections(definition("CustomBroker", "KoreaStockBrokerNode")["nodes"])
    assert len(errors) == 1
    assert errors[0].details["max_broker_connections"] == 1
