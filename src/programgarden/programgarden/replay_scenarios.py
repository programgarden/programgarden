"""Assess expected negative outcomes without rewriting raw execution failures.

Only a trusted fixture may describe the exact order failures it is testing.
Contracts, mapping errors, unrelated failures and unobserved expectations cannot
be waived. A negative scenario PASS is distinct from successful order execution.
"""
from collections import Counter

from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.validation_replay import content_hash
from programgarden.replay_order_adapter import ORDER_NODES


def check_financial_expectations(simulation, schema):
    required = {"cash", "reserved_cash", "positions", "orders", "live_order_count"}
    if not isinstance(schema, dict):
        raise ContractViolation("expected_simulation", "Order graphs require financial-state assertions", "REPLAY_EXPECTATIONS_REQUIRED")
    check_contract(simulation, schema, "expected_simulation")
    if (not required <= set(schema.get("required", []))
            or not required <= schema.get("properties", {}).keys()):
        raise ContractViolation("expected_simulation", "Order graphs require independent cash, reservation, position and order-state assertions", "REPLAY_EXPECTATIONS_REQUIRED")
    if simulation.get("live_order_count") != 0:
        raise ContractViolation("live_order_count", "Replay must never submit live orders")


def check_final_expectations(result, fixture, graph):
    """Final acceptance asserts outputs and financial state, not just no error."""
    expected = fixture.get("expected")
    if not isinstance(expected,dict) or not expected:
        raise ContractViolation("expected", "Final replay requires independent expected-result assertions", "REPLAY_EXPECTATIONS_REQUIRED")
    # The initial fixture's expectations describe the INITIAL run: evaluate them
    # against the outputs/executed captured at the end of the main flow, before any
    # events frame re-executed or cleared a downstream branch. Frame expectations
    # (below) use each frame's own post-frame snapshot; the simulated book stays
    # cumulative on the FINAL state.
    for node_id, schema in expected.items():
        check_contract(result.initial_outputs.get(node_id), schema, f"{node_id}.expected")
    for node_id in fixture.get("must_execute", []):
        if node_id not in result.initial_executed:
            raise ContractViolation(node_id, "Required path was not reached")
    from programgarden.replay_events import checked_events
    events = checked_events(fixture)
    if len(events) != len(result.events):
        raise ContractViolation("events", "Every declared final replay event must be observed")
    has_orders = any(node["type"] in ORDER_NODES for node in graph["nodes"])
    for index, (event, observed) in enumerate(zip(events, result.events)):
        if (observed.get("index") != index or any(observed.get(key) != event[key]
                for key in ("as_of", "type", "source_node_id"))):
            raise ContractViolation("events", "Event evidence does not match the recorded timeline")
        assertions = event.get("expected")
        if not isinstance(assertions, dict) or not assertions or not event.get("must_execute"):
            raise ContractViolation("events", "Each final event requires independent results and path coverage",
                                    "REPLAY_EXPECTATIONS_REQUIRED")
        for node_id, schema in assertions.items():
            check_contract(observed["outputs"].get(node_id), schema, f"events.{index}.{node_id}")
        if not set(event["must_execute"]) <= set(observed["executed"]):
            raise ContractViolation("events", "Required event path was not reached")
        if has_orders:
            check_financial_expectations(observed["simulation"], event.get("expected_simulation"))
    if has_orders:
        check_financial_expectations(result.simulation, fixture.get("expected_simulation"))


def assess_scenario(result, fixture, graph):
    expected = fixture.get("expected_order_failures", [])
    check_contract(expected,{"type":"array","items":{"type":"object",
        "required":["node_id","symbol_key","status","reason","filled_quantity"],
        "additionalProperties":False,"properties":{
            "node_id":{"type":"string","minLength":1},
            "symbol_key":{"type":"string","minLength":1},
            "status":{"type":"string","enum":["rejected","unknown"]},
            "reason":{"type":["string","null"]},
            "filled_quantity":{"type":"integer","minimum":0}}}},"expected_order_failures")
    node_ids={node["id"] for node in graph["nodes"]}
    relevant=[failure for failure in expected if failure["node_id"] in node_ids]
    observed=[{key:order[key] for key in ("node_id","symbol_key","status","reason","filled_quantity")}
              for order in result.order_observations if order["status"] in {"rejected","unknown"}]
    if Counter(map(content_hash,relevant)) != Counter(map(content_hash,observed)):
        return False
    if not result.errors:
        return result.passed
    if not relevant:
        return False
    failed_nodes={failure["node_id"] for failure in observed}
    for error in result.errors:
        if error.get("node_id") not in failed_nodes:
            return False
        if error.get("code")=="REPLAY_NODE_FAILED":
            messages={"order_failed" + (": " + failure["reason"] if failure["reason"] else "")
                      for failure in observed if failure["node_id"]==error["node_id"]}
            if error.get("message") in messages:
                continue
        if error.get("code")=="REPLAY_ORDER_NOT_ACCEPTED":
            matching=[order for order in result.order_observations
                      if order["node_id"]==error["node_id"] and order["order_id"]==error.get("order_id")]
            if len(matching)==1 and all(error.get(key)==matching[0][key] for key in ("status","reason")):
                continue
        return False
    return True


def scenario_receipt(result, fixture, graph):
    """Return an assessment, retaining every raw error on the replay result."""
    try:
        passed=assess_scenario(result,fixture,graph)
        errors=[] if passed else [{"code":"REPLAY_SCENARIO_FAILED", "message":"Observed outcome differs from the fixture expectation"}]
        if passed:
            # Use existing independent value assertions as soon as their node is
            # actually executed. Waiting for finalization would mark a numerically
            # wrong (but schema-valid) dependency VERIFIED in the meantime. The
            # initial fixture's expected describes the initial run, so gate on the
            # main-flow executed set and read the pre-events (initial) outputs.
            reached = set(result.initial_executed)
            for node_id, schema in fixture.get("expected", {}).items():
                if node_id in reached:
                    check_contract(result.initial_outputs.get(node_id), schema, f"{node_id}.expected")
            declared = fixture.get("events", [])
            for event in result.events:
                index = event["index"]
                if type(index) is not int or not 0 <= index < len(declared):
                    raise ContractViolation("events", "Unknown event evidence")
                for node_id, schema in declared[index].get("expected", {}).items():
                    if node_id in event["executed"]:
                        check_contract(event["outputs"].get(node_id), schema, f"events.{index}.{node_id}.expected")
    except ContractViolation as exc:
        passed,errors=False,[exc.as_dict()]
    return {"scenario_passed":passed,"scenario_errors":errors}
