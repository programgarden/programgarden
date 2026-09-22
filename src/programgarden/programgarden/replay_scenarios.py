"""Assess expected negative outcomes without rewriting raw execution failures.

Only a trusted fixture may describe the exact order failures it is testing.
Contracts, mapping errors, unrelated failures and unobserved expectations cannot
be waived. A negative scenario PASS is distinct from successful order execution.
"""
from collections import Counter

from programgarden.replay_contracts import ContractViolation, check_contract
from programgarden.validation_replay import content_hash


def assess_scenario(result, fixture, graph):
    expected = fixture.get("expected_order_failures", [])
    check_contract(expected,{"type":"array","items":{"type":"object",
        "required":["node_id","symbol_key","status","reason","filled_quantity"],
        "additionalProperties":False,"properties":{
            "node_id":{"type":"string","minLength":1},
            "symbol_key":{"type":"string","minLength":1},
            "status":{"type":"string","enum":["rejected","unknown"]},
            "reason":{"type":["string","null"]},
            "filled_quantity":{"type":"integer","const":0}}}},"expected_order_failures")
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
    except ContractViolation as exc:
        passed,errors=False,[exc.as_dict()]
    return {"scenario_passed":passed,"scenario_errors":errors}
