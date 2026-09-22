"""Deterministic contracts at replay input, mapping and output boundaries.

Contracts use an intentionally bounded JSON-schema subset. Unknown constraints
fail closed; values are never coerced, defaulted, renamed or replaced with zero.
Semantic identity is explicit contract data, not inferred from field names.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any

CONTRACT_VERSION = "replay-contract-1"
_KEYS = frozenset({"type", "nullable", "required", "properties", "items", "enum",
                   "minimum", "maximum", "minItems", "maxItems", "minLength",
                   "maxLength", "const", "additionalProperties", "format",
                   "decimalPlaces", "description"})
_TYPES = {"object": dict, "array": list, "string": str, "number": (int, float),
          "integer": int, "boolean": bool, "null": type(None)}


class ContractViolation(ValueError):
    def __init__(self, path: str, reason: str, code: str = "REPLAY_CONTRACT_FAILED"):
        self.path, self.reason, self.code = path, reason, code
        super().__init__(f"{path}: {reason}")

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": str(self)}


def finite_json(value: Any, path: str = "$", depth: int = 0) -> None:
    if depth > 40:
        raise ContractViolation(path, "JSON nesting exceeds the validation limit")
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractViolation(path, "NaN and Infinity are not valid evidence")
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractViolation(path, "Object keys must be strings")
            finite_json(item, f"{path}.{key}", depth + 1)
        return
    if type(value) is list:
        for index, item in enumerate(value):
            finite_json(item, f"{path}[{index}]", depth + 1)
        return
    raise ContractViolation(path, "Expected finite JSON data")


def check_contract(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Validate a finite JSON value without coercion; raise at the first defect."""
    finite_json(value, path)
    finite_json(schema, "contract")
    _validate_schema(schema, "contract", 0)
    _check(value, schema, path, 0)


def _literal_equal(left, right):
    """JSON identities do not coerce nested True/1 or False/0 values."""
    if type(left) in (int,float) and type(right) in (int,float):
        return Decimal(str(left))==Decimal(str(right))
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys()==right.keys() and all(_literal_equal(left[key],right[key]) for key in left)
    if isinstance(left, list):
        return len(left)==len(right) and all(_literal_equal(a,b) for a,b in zip(left,right))
    return left==right


def _validate_schema(schema: Any, path: str, depth: int) -> None:
    def invalid(reason):
        raise ContractViolation(path, reason, "REPLAY_CONTRACT_UNSUPPORTED")
    if depth > 40 or type(schema) is not dict or set(schema) - _KEYS:
        invalid("Unsupported contract")
    kinds = schema.get("type")
    kinds = kinds if type(kinds) is list else [kinds]
    if not kinds or any(type(k) is not str or k not in _TYPES for k in kinds):
        invalid("Explicit supported type required")
    if len(kinds) != len(set(kinds)):
        invalid("Duplicate types are not supported")
    for key in ("nullable", "additionalProperties"):
        if key in schema and type(schema[key]) is not bool:
            invalid(f"{key} must be boolean")
    if "enum" in schema and (type(schema["enum"]) is not list or not schema["enum"]):
        invalid("enum must be a nonempty array")
    for key in ("minItems", "maxItems", "minLength", "maxLength", "decimalPlaces"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            invalid(f"{key} must be a nonnegative integer")
    if schema.get("decimalPlaces", 0) > 18:
        invalid("decimalPlaces must not exceed 18")
    for key in ("minimum", "maximum"):
        if key in schema and type(schema[key]) not in (int, float):
            invalid(f"{key} must be a finite number")
    for lower, upper in (("minimum", "maximum"), ("minItems", "maxItems"), ("minLength", "maxLength")):
        if lower in schema and upper in schema and schema[lower] > schema[upper]:
            invalid(f"{lower} exceeds {upper}")
    applicable = {"object": {"properties", "required", "additionalProperties"},
                  "array": {"items", "minItems", "maxItems"},
                  "string": {"minLength", "maxLength", "format"},
                  "number": {"minimum", "maximum", "decimalPlaces"},
                  "integer": {"minimum", "maximum", "decimalPlaces"}}
    allowed = {"type", "nullable", "const", "enum", "description"}
    for kind in kinds:
        allowed |= applicable.get(kind, set())
    if set(schema) - allowed:
        invalid("Constraint does not apply to the declared type")
    if "description" in schema and type(schema["description"]) is not str:
        invalid("description must be a string")
    if "format" in schema and schema["format"] != "date-time":
        invalid("Unsupported format")
    if "properties" in schema:
        if type(schema["properties"]) is not dict:
            invalid("properties must be an object")
        for name, child in schema["properties"].items():
            _validate_schema(child, f"{path}.properties.{name}", depth + 1)
    if "required" in schema:
        required = schema["required"]
        if type(required) is not list or any(type(k) is not str for k in required):
            invalid("required must contain field names")
        if len(required) != len(set(required)):
            invalid("required contains duplicates")
    if "items" in schema:
        _validate_schema(schema["items"], f"{path}.items", depth + 1)


def _check(value: Any, schema: dict[str, Any], path: str, depth: int) -> None:
    if depth > 40 or not isinstance(schema, dict) or set(schema) - _KEYS:
        raise ContractViolation(path, "Unsupported contract", "REPLAY_CONTRACT_UNSUPPORTED")
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if not kinds or any(not isinstance(k, str) or k not in _TYPES for k in kinds):
        raise ContractViolation(path, "Explicit supported type required", "REPLAY_CONTRACT_UNSUPPORTED")
    matches = (value is None and schema.get("nullable") is True) or any(isinstance(value, _TYPES[k]) and
                  not (k in ("number", "integer") and isinstance(value, bool)) for k in kinds)
    if not matches:
        raise ContractViolation(path, f"Expected {kind}, received {type(value).__name__}")
    if "const" in schema and not _literal_equal(value,schema["const"]):
        raise ContractViolation(path, "Value does not match the required identity")
    if "enum" in schema and not any(_literal_equal(value,v) for v in schema["enum"]):
        raise ContractViolation(path, "Value is outside the allowed enumeration")
    if isinstance(value, dict):
        properties, required = schema.get("properties", {}), schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise ContractViolation(path, "Invalid object contract", "REPLAY_CONTRACT_UNSUPPORTED")
        for key in required:
            if key not in value:
                raise ContractViolation(f"{path}.{key}", "Required field is absent")
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], f"{path}.{key}", depth + 1)
            elif schema.get("additionalProperties") is False:
                raise ContractViolation(f"{path}.{key}", "Undeclared field")
    elif isinstance(value, list):
        for key, valid in (("minItems", len(value) >= schema.get("minItems", 0)),
                           ("maxItems", len(value) <= schema.get("maxItems", len(value)))):
            if not valid:
                raise ContractViolation(path, f"Array violates {key}")
        if "items" in schema:
            for index, item in enumerate(value):
                _check(item, schema["items"], f"{path}[{index}]", depth + 1)
    elif type(value) in (float, int):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            raise ContractViolation(path, "Number is outside the allowed range")
        if "decimalPlaces" in schema:
            places = schema["decimalPlaces"]
            if type(places) is not int or not 0 <= places <= 18:
                raise ContractViolation(path, "Invalid precision contract", "REPLAY_CONTRACT_UNSUPPORTED")
            try:
                precision = max(0, -Decimal(str(value)).normalize().as_tuple().exponent)
            except InvalidOperation as exc:
                raise ContractViolation(path, "Invalid decimal") from exc
            if precision > places:
                raise ContractViolation(path, "Number exceeds the allowed decimal precision")
    elif isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value)):
            raise ContractViolation(path, "String length violates the contract")
        if "format" in schema:
            if schema["format"] != "date-time":
                raise ContractViolation(path, "Unsupported format", "REPLAY_CONTRACT_UNSUPPORTED")
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractViolation(path, "Expected an ISO timestamp") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ContractViolation(path, "Timestamp must include its timezone")


def check_observation_identity(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Check explicit units and time identity at a data boundary.

    The caller supplies only the semantics consumed by this boundary. A currency
    conversion is a separate transformation with its own tested output contract.
    Missing metadata is unverified, not inferred as USD/UTC from node names.
    """
    allowed = {"symbol", "market", "currency", "timeframe", "as_of"}
    if not expected or set(expected) - allowed:
        raise ContractViolation("metadata", "Unsupported semantic identity", "REPLAY_CONTRACT_UNSUPPORTED")
    for field, value in expected.items():
        check_contract(actual.get(field), {"type": "string", "const": value,
                       **({"format": "date-time"} if field == "as_of" else {})}, f"metadata.{field}")


def check_codenode_ports(ports: Any) -> None:
    if not isinstance(ports, list):
        raise ContractViolation("outputs", "Declared CodeNode ports must be a list of objects")
    names: set[str] = set()
    for index, port in enumerate(ports):
        if not isinstance(port, dict) or not isinstance(port.get("name"), str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", port["name"]):
            raise ContractViolation(f"outputs[{index}]", "Invalid declared output port")
        if port["name"] in names or port.get("type", "any") not in {*_TYPES, "any"}:
            raise ContractViolation(f"outputs[{index}]", "Duplicate name or unsupported output type")
        names.add(port["name"])
