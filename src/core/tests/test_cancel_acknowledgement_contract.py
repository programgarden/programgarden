"""Published node metadata cannot teach unconfirmed cancel-and-replace execution."""

import pytest
from programgarden_core.registry import NodeTypeRegistry


@pytest.mark.parametrize("kind", ["OverseasStock", "OverseasFutures", "KoreaStock"])
def test_cancellation_catalog_matches_acknowledgement_contract(kind):
    schema = NodeTypeRegistry().get_schema(kind + "CancelOrderNode")
    port = next(port for port in schema.outputs if port["name"] == "cancel_result")
    fields = {field["name"] for field in port["fields"]}
    assert {"success", "status", "confirmation_pending", "order_id", "cancel_order_no"} <= fields
    assert "confirmation_pending" in schema.node_guide["output_consumption"]
    for example in schema.examples:
        assert "accepted" in example["expected_output"]
        assert all(not node["type"].endswith("NewOrderNode") for node in example["workflow_snippet"]["nodes"])
