"""Failed contract assertions carry the observed value and the failing scenario.

A candidate that returns {'allowed': None} where the scenario expects a boolean
identity used to fail with "guard.expected.allowed: Value does not match the
required identity" and no scenario id and no observed value. The diagnostic now
attaches detail {scenario_id, path, observed, constraint_kind, observed_type}
(NEVER the expected value — the oracle stays hidden) and each per-run summary
carries scenario_id, so the host can name the failing scenario.
"""
import pytest

from programgarden.replay_contracts import ContractViolation, check_contract
from tests.test_incremental_build import append, code, BuildWorkspace


# ── check_contract detail: observed value + constraint kind, no oracle ──────

def test_identity_failure_carries_observed_not_expected():
    # Reproduces the reported case: allowed=None against a boolean identity.
    schema = {"type": "object", "required": ["allowed"], "properties": {
        "allowed": {"type": "boolean", "nullable": True, "const": True}}}
    with pytest.raises(ContractViolation) as exc:
        check_contract({"allowed": None}, schema, "guard.expected")
    assert exc.value.code == "REPLAY_CONTRACT_FAILED"
    assert exc.value.detail == {"path": "guard.expected.allowed", "observed": "null",
                                "constraint_kind": "identity", "observed_type": "NoneType"}
    # The oracle (True) never appears in the message or detail.
    assert "True" not in str(exc.value) and "True" not in str(exc.value.detail)


@pytest.mark.parametrize("value,schema,kind,observed,otype", [
    (False, {"type": "boolean", "const": True}, "identity", "false", "bool"),
    ("BUY", {"type": "string", "enum": ["SELL"]}, "enum", "BUY", "str"),
    (None, {"type": "boolean"}, "type", "null", "NoneType"),
    (7, {"type": "number", "maximum": 5}, "range", "7", "int"),
])
def test_constraint_kinds_report_observed_value(value, schema, kind, observed, otype):
    with pytest.raises(ContractViolation) as exc:
        check_contract(value, schema, "p")
    d = exc.value.detail
    assert d["constraint_kind"] == kind
    assert d["observed"] == observed and d["observed_type"] == otype
    assert d["path"] == "p"


def test_required_field_absence_reports_present_keys_only():
    schema = {"type": "object", "required": ["allowed"], "properties": {
        "allowed": {"type": "boolean"}}}
    with pytest.raises(ContractViolation) as exc:
        check_contract({"other": 1}, schema, "guard.expected")
    d = exc.value.detail
    assert d["constraint_kind"] == "required" and d["observed"] == "<absent>"
    assert d["present_keys"] == ["other"]


def test_observed_value_is_bounded():
    big = {"v": "x" * 5000}
    schema = {"type": "object", "properties": {"v": {"type": "number"}}}
    with pytest.raises(ContractViolation) as exc:
        check_contract(big, schema, "p")
    assert len(exc.value.detail["observed"]) <= 220
    assert exc.value.detail["observed"].endswith("…(truncated)")


# ── scenario_id threading through runs and error detail ─────────────────────

def _ws(fixture):
    return BuildWorkspace("task", 1, {"id": "wf", "name": "wf", "nodes": [], "edges": []}, [fixture])


@pytest.mark.asyncio
async def test_runs_and_scenario_errors_carry_named_scenario_id():
    ws = _ws({"scenario_id": "duplicate", "expected": {"one": {"type": "object", "required": ["result"],
              "properties": {"result": {"type": "number", "const": 999}}}}})
    await append(ws, {"id": "start", "type": "StartNode"})
    proof = await append(ws, code("one", "1"), "start")  # emits result=1, scenario expects 999
    assert not proof["passed"]
    assert proof["runs"] and all(r.get("scenario_id") == "duplicate" for r in proof["runs"])
    err = next(e for e in proof["errors"] if isinstance(e.get("detail"), dict))
    assert err["scenario_id"] == "duplicate"
    assert err["detail"]["scenario_id"] == "duplicate"
    assert err["detail"]["path"].endswith("one.expected.result")
    assert err["detail"]["constraint_kind"] == "identity"
    assert err["detail"]["observed"] == "1" and err["detail"]["observed_type"] == "int"
    assert "999" not in str(err)  # the expected value is never surfaced


@pytest.mark.asyncio
async def test_positional_scenario_id_when_suite_gives_none():
    ws = _ws({"expected": {"one": {"type": "object", "required": ["result"],
              "properties": {"result": {"type": "number", "const": 999}}}}})
    await append(ws, {"id": "start", "type": "StartNode"})
    proof = await append(ws, code("one", "1"), "start")
    assert not proof["passed"]
    assert all(r.get("scenario_id") == "scenario[0]" for r in proof["runs"])
    err = next(e for e in proof["errors"] if isinstance(e.get("detail"), dict))
    assert err["detail"]["scenario_id"] == "scenario[0]"
