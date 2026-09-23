"""Reserved top-level output keys (`error`, `reason`) fail with explicit detail.

The live runtime and this replay both treat a top-level `error` value, and a
top-level `reason` in the invalid-input set, as a node failure. A CodeNode that
independently designs a port named `error`/`reason` therefore reads as an engine
failure. The failure stays a ContractViolation with the same code, but now names
the reserved key, previews the node's own output value and flags whether a
CodeNode port declared it, so the chatbot repairs the naming instead of guessing.
"""
import pytest

from programgarden.validation_replay import replay, _reserved_key_detail
from tests.test_validation_replay import workflow, code


def code_node(node_id, ports, ret):
    return {"id": node_id, "type": "CodeNode", "outputs": ports,
            "code": f"def execute(data, params, context):\n return {ret}"}


@pytest.mark.asyncio
async def test_error_port_failure_names_the_reserved_key_and_blocks_downstream():
    node = code_node("calc", [{"name": "error", "type": "string"}], "{'error': 'boom detail'}")
    result = await replay(workflow(node, code("next")), {})
    assert not result.passed and "next" not in result.executed
    err = next(e for e in result.errors if e.get("node_id") == "calc")
    assert err["code"] == "REPLAY_CONTRACT_FAILED"  # semantics unchanged
    assert err["detail"] == {"reserved_key": "error", "value": "boom detail", "declared_output_port": True}
    assert "reserved" in err["message"] and "`error`" in err["message"] and "`reason`" in err["message"]


@pytest.mark.asyncio
async def test_reason_invalid_input_names_the_reserved_key():
    node = code_node("calc", [{"name": "reason", "type": "string"}], "{'reason': 'no_price'}")
    result = await replay(workflow(node), {})
    assert not result.passed
    err = next(e for e in result.errors if e.get("node_id") == "calc")
    assert err["code"] == "REPLAY_CONTRACT_FAILED"
    assert err["detail"] == {"reserved_key": "reason", "value": "no_price", "declared_output_port": True}
    assert "no_price" in err["message"] and "reserved" in err["message"]


def test_reserved_key_detail_bounds_value_and_flags_declared_port():
    # A declared CodeNode port named for the reserved key is flagged; a long value
    # is bounded; a genuine runtime error from a non-CodeNode is not a port clash.
    big = _reserved_key_detail("error", "x" * 500, "CodeNode", {"outputs": [{"name": "error"}]})
    assert big["reserved_key"] == "error" and big["declared_output_port"] is True
    assert big["value"].endswith("…(truncated)") and len(big["value"]) <= 220
    runtime = _reserved_key_detail("error", "broker rejected", "PositionSizingNode", {})
    assert runtime == {"reserved_key": "error", "value": "broker rejected", "declared_output_port": False}
    other_port = _reserved_key_detail("reason", "no_price", "CodeNode", {"outputs": [{"name": "result"}]})
    assert other_port["declared_output_port"] is False
    # A non-string value is serialized, not dropped.
    structured = _reserved_key_detail("error", {"code": 7}, "CodeNode", {})
    assert structured["value"] == '{"code":7}'


@pytest.mark.asyncio
async def test_ordinary_codenode_output_is_unaffected():
    result = await replay(workflow(code("calc", "1")), {})
    assert result.passed, result.errors
    assert result.outputs["calc"]["result"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("ret,preview", [("{'error': None}", "None"), ("{'error': ''}", "")])
async def test_present_error_key_fails_for_computation_nodes_even_when_falsy(ret, preview):
    # Matches the live node_runner rule (`"error" in result`): a present top-level
    # `error` key is a failure regardless of value, so {"error": None} no longer
    # certifies behavior the production runtime rejects.
    # Untyped port so the falsy value reaches the reserved-key check rather than the
    # declared-port type check (a typed `string` port would reject None on its own).
    node = code_node("calc", [{"name": "error"}], ret)
    result = await replay(workflow(node), {})
    assert not result.passed
    err = next(e for e in result.errors if e.get("node_id") == "calc")
    assert err["code"] == "REPLAY_CONTRACT_FAILED"
    assert err["detail"] == {"reserved_key": "error", "value": preview, "declared_output_port": True}


@pytest.mark.asyncio
@pytest.mark.parametrize("quantity", [0, 2])
async def test_native_success_envelope_with_error_none_still_passes(quantity):
    # OverseasFuturesOrderableQuantityNode (a SOURCE node) returns a success
    # envelope {"quantity", "verified": True, "error": None}. The presence rule is
    # scoped to computation nodes, so this native `error: None` is not a failure.
    from tests.test_futures_orderable_evidence import config, response
    from tests.test_replay_sources import futures_case
    node = {"id": "capacity", "type": "OverseasFuturesOrderableQuantityNode", **config()}
    node.pop("connection")
    source = response(quantity).model_dump(mode="json", exclude_unset=True)
    result = await replay(*futures_case(node, source))
    assert result.passed, result.errors
    assert result.outputs["capacity"] == {"quantity": quantity, "verified": True, "error": None}
