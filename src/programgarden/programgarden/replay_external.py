"""Explicit external recordings bound to resolved requests, with no transport."""

from copy import deepcopy
import json

from programgarden.replay_contracts import ContractViolation, check_contract


_PRESENTATION_FIELDS = {"id", "name", "description", "position", "category"}
_SCHEDULER_FIELDS = {"_source_node_id", "_trigger_on_update_nodes", "_branch_scope"}


def request_identity(node_type, config):
    """Normalize schema defaults, retaining every executable request parameter.

    This is deliberately not an inferred broker request. Both recordings and
    execution refer to the native node schema. A URL, body, date range, timeframe,
    symbol, filter or paper mode change must select another approved recording.
    """
    from programgarden_core import NodeTypeRegistry
    from pydantic import ValidationError

    node_class = NodeTypeRegistry().get(node_type)
    if node_class is None or not isinstance(config, dict):
        raise ContractViolation("request", "Unknown recording node schema", "REPLAY_FIXTURE_INVALID")
    try:
        node = node_class.model_validate_json(
            json.dumps({**config, "id": "recording", "type": node_type}, allow_nan=False), strict=True)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ContractViolation("request", "Invalid resolved recording request", "REPLAY_FIXTURE_INVALID") from exc
    # Reject unknown parameters instead of letting BaseModel's extra policy
    # silently remove a field the live executor may consume.
    if set(config) - set(node_class.model_fields) - {"connection"} - _SCHEDULER_FIELDS - _PRESENTATION_FIELDS:
        raise ContractViolation("request", "Unknown recording request fields", "REPLAY_FIXTURE_INVALID")
    result = node.model_dump(mode="json", exclude=_PRESENTATION_FIELDS | _SCHEDULER_FIELDS | {"connection"})
    return result


def recording(node_type, config, output, contract, *, as_of, item=None, order_events=None):
    """Construct an explicit fixture at a trusted provisioning boundary.

    This helper does not establish provenance. The host must never expose its
    arguments to a model as editable validation data or use a candidate's output
    as the expected result. Request matching is enforced again inside the worker.
    """
    check_contract(as_of, {"type": "string", "format": "date-time"}, "recording.as_of")
    check_contract(output, contract, "recording.output")
    result = {"request": request_identity(node_type, config), "as_of": as_of,
              "item": deepcopy(item), "output": deepcopy(output), "contract": deepcopy(contract)}
    if order_events is not None:
        result["order_events"] = deepcopy(order_events)
    return result


def external_record(fixture, node_id, node_type, config, context):
    record = fixture.get("nodes", {}).get(node_id)
    if not isinstance(record, dict):
        raise ContractViolation(node_id, "An explicit external recording is required", "REPLAY_FIXTURE_REQUIRED")
    if context._iteration_total:
        item = context._iteration_item
        if not isinstance(item, dict) or not isinstance(item.get("symbol"), str) or not item["symbol"]:
            raise ContractViolation(node_id, "An iterated recording requires symbol identity", "REPLAY_FIXTURE_REQUIRED")
        exchange = item.get("exchange")
        if not exchange and node_type.startswith("KoreaStock"):
            # The actual domestic schemas accept {symbol} without exchange.
            exchange = "KRX"
        if not isinstance(exchange, str) or not exchange:
            raise ContractViolation(node_id, "An overseas recording requires exchange identity", "REPLAY_FIXTURE_REQUIRED")
        record = record.get("items", {}).get(exchange + ":" + item["symbol"])
    if not isinstance(record, dict):
        raise ContractViolation(node_id, "No matching per-item recording", "REPLAY_FIXTURE_REQUIRED")
    if "request" not in record or "as_of" not in record or "item" not in record:
        raise ContractViolation(node_id, "An input-bound recording is required", "REPLAY_FIXTURE_REQUIRED")
    from programgarden.validation_replay import content_hash
    if content_hash(record["request"]) != content_hash(request_identity(node_type, config)):
        raise ContractViolation(node_id, "Recording does not match the resolved node request", "REPLAY_FIXTURE_MISMATCH")
    if not context.validation_as_of or record["as_of"] != context.validation_as_of:
        raise ContractViolation(node_id, "Recording does not match the shared replay clock", "REPLAY_FIXTURE_MISMATCH")
    item = context._iteration_item if context._iteration_total else None
    if content_hash(record["item"]) != content_hash(item):
        raise ContractViolation(node_id, "Recording does not match the actual iteration item", "REPLAY_FIXTURE_MISMATCH")
    return record
