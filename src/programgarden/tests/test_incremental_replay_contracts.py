"""Boundary regressions, including the false-PASS CodeNode declaration."""
import pytest

from programgarden import ProgramGarden
from programgarden.replay_contracts import ContractViolation, check_contract, check_observation_identity


@pytest.mark.parametrize("value,schema", [
    ({"price": 10}, {"type": "object", "required": ["close_price"]}),
    ({"ticker": "TEST"}, {"type": "object", "required": ["symbol"]}),
    ("10", {"type": "number"}), (True, {"type": "integer"}),
    (None, {"type": "number"}), (float("nan"), {"type": "number"}),
    ({"price": float("inf")}, {"type": "object"}),
    ([1,2], {"type": "array", "minItems": 3}),
    (0, {"type": "integer", "minimum": 1}),
    (1.234, {"type": "number", "decimalPlaces": 2}),
    ("2026-09-22T10:00:00", {"type": "string", "format": "date-time"}),
    ("limit_typo", {"type": "string", "enum": ["limit", "market"]}),
])
def test_wrong_boundary_fails_without_coercion(value, schema):
    with pytest.raises(ContractViolation):
        check_contract(value, schema)


@pytest.mark.parametrize("field,actual,expected", [
    ("currency", "KRW", "USD"), ("timeframe", "1m", "5m"),
    ("market", "korea_stock", "overseas_stock"), ("symbol", "A", "B"),
    ("as_of", "2026-09-22T10:00:00+09:00", "2026-09-22T10:00:00Z"),
])
def test_unit_or_timestamp_identity_mismatch(field, actual, expected):
    with pytest.raises(ContractViolation):
        check_observation_identity({field:actual}, {field:expected})


def test_finite_explicit_nullable_and_zero_are_preserved():
    check_contract({"rsi": None, "quantity": 0}, {
        "type": "object", "required": ["rsi", "quantity"],
        "properties": {"rsi": {"type":"number", "nullable":True},
                       "quantity": {"type":"integer", "minimum":0}}})


def graph(ports):
    return {"id":"contract", "name":"Contract", "nodes":[
        {"id":"start", "type":"StartNode"},
        {"id":"code", "type":"CodeNode", "outputs":ports,
         "code":"def execute(data, params, context):\n return {'result': {'signal':'buy'}}"}],
        "edges":[{"from":"start", "to":"code"}]}


@pytest.mark.parametrize("ports", [{"result":"object"}, ["result"],
    [{"name":"result","type":"object"},{"name":"result","type":"object"}],
    [{"type":"object"}]])
def test_mapping_or_invalid_port_declaration_cannot_silently_double_wrap(ports):
    result=ProgramGarden().validate(graph(ports))
    assert not result.is_valid
    assert any(e.location.field_path == "outputs" for e in result.errors)


@pytest.mark.parametrize("ports", [[], [{"name":"result","type":"object"}]])
def test_real_declared_port_contract_remains_supported(ports):
    assert ProgramGarden().validate(graph(ports)).is_valid


@pytest.mark.parametrize("schema", [
    {"type":"object", "properties":{"unused":{"type":"invented"}}},
    {"type":"array", "items":{"type":"string", "format":"invented"}},
    {"type":"string", "minItems":1},
    {"type":"number", "minimum":"0"},
    {"type":"number", "minimum":10, "maximum":1},
    {"type":"array", "minItems":True},
    {"type":"object", "additionalProperties":{}},
    {"type":"string", "nullable":"yes"},
    {"type":"string", "enum":None},
])
def test_invalid_contract_is_rejected_even_without_observed_values(schema):
    from programgarden.replay_contracts import check_contract, ContractViolation
    with pytest.raises(ContractViolation) as exc:
        check_contract(None, {"nullable":True, **schema})
    assert exc.value.code == "REPLAY_CONTRACT_UNSUPPORTED"


def test_nullable_does_not_bypass_identity_or_enum():
    from programgarden.replay_contracts import check_contract, ContractViolation
    with pytest.raises(ContractViolation):
        check_contract(None, {"type":"string","nullable":True,"const":"USD"})
    with pytest.raises(ContractViolation):
        check_contract(None, {"type":"string","nullable":True,"enum":["USD"]})


@pytest.mark.asyncio
@pytest.mark.parametrize("value,ports", [
    ("{'result': '3'}",[{"name":"result","type":"number"}]),
    ("{'other': 3}",[{"name":"result","type":"any"}]),
    ("{'result': None}",[{"name":"result","type":"number"}]),
])
async def test_existing_deep_path_cannot_report_wrong_or_missing_declared_output_as_valid(value,ports):
    definition=graph(ports)
    definition["nodes"][1]["code"]="def execute(data, params, context):\n return "+value
    result=await ProgramGarden().executor.deep_validate(definition)
    assert not result.is_valid


@pytest.mark.parametrize("constraint",["const","enum"])
def test_nested_expected_identity_does_not_coerce_boolean_and_quantity(constraint):
    expected=[{"quantity":1,"accepted":False}]
    schema={"type":"array",constraint:expected if constraint=="const" else [expected]}
    check_contract(expected,schema)
    with pytest.raises(ContractViolation):
        check_contract([{"quantity":True,"accepted":0}],schema)


def test_json_numeric_identity_accepts_equal_numbers_without_accepting_boolean():
    check_contract({"price":3.0},{"type":"object","const":{"price":3}})
    with pytest.raises(ContractViolation):
        check_contract(True,{"type":["boolean","integer"],"const":1})
