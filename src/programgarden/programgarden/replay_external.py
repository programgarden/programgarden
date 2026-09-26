"""Explicit external recordings bound to resolved requests, with no transport."""

from copy import deepcopy
import json

from programgarden.replay_contracts import ContractViolation, check_contract


_PRESENTATION_FIELDS = {"id", "name", "description", "position", "category"}
_SCHEDULER_FIELDS = {"_source_node_id", "_trigger_on_update_nodes", "_branch_scope"}

# Bound the diagnostic so a large recording cannot produce an unbounded diff or
# message. The full evidence still names every top-level/one-level difference up
# to these caps; both operands are already non-secret normalized identities.
_MAX_DIFF_PATHS = 24
_MAX_MESSAGE_PATHS = 6
_ABSENT = object()


def _canon(value):
    """The exact canonical form ``content_hash`` compares, without hashing.

    Using it as the equality relation means the diff reports a difference on
    exactly the paths that made the two recordings' hashes disagree, including
    JSON identities such as ``1`` versus ``1.0`` that Python ``==`` would merge.
    """
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _differing_paths(recorded, resolved):
    """Deterministic top-level and one-level-nested key diff of two JSON objects.

    Reports top-level keys present on only one side and, for keys that are
    objects on both sides (``symbol``, ``connection``, ``config`` and the like),
    the differing nested keys as ``key.subkey``. Both operands are normalized
    request identities or iteration items, so no credential secret can appear.
    """
    rec = recorded if isinstance(recorded, dict) else {}
    res = resolved if isinstance(resolved, dict) else {}
    paths: list[str] = []
    for key in sorted(set(rec) | set(res)):
        in_rec, in_res = key in rec, key in res
        if in_rec and in_res and _canon(rec[key]) == _canon(res[key]):
            continue
        if in_rec and in_res and isinstance(rec[key], dict) and isinstance(res[key], dict):
            for sub in sorted(set(rec[key]) | set(res[key])):
                a, b = rec[key].get(sub, _ABSENT), res[key].get(sub, _ABSENT)
                if a is _ABSENT or b is _ABSENT or _canon(a) != _canon(b):
                    paths.append(f"{key}.{sub}")
        else:
            paths.append(key)
    return paths


def _project(source, paths):
    """Copy only the given dotted paths out of ``source``; absent paths are omitted."""
    out: dict = {}
    for path in paths:
        head, _, tail = path.partition(".")
        if not isinstance(source, dict) or head not in source:
            continue
        if tail:
            branch = out.setdefault(head, {})
            if isinstance(source[head], dict) and tail in source[head]:
                branch[tail] = deepcopy(source[head][tail])
        else:
            out[head] = deepcopy(source[head])
    return out


def mismatch_detail(recorded, resolved):
    """Secret-free field-level diff of an object recording against its resolution.

    Returns ``{"recorded", "resolved", "differing"}`` where ``differing`` is the
    bounded, sorted list of dotted paths and the two projections carry only the
    values at those paths. Callers hand it already-normalized identities/items.
    """
    differing = _differing_paths(recorded, resolved)[:_MAX_DIFF_PATHS]
    return {"recorded": _project(recorded, differing),
            "resolved": _project(resolved, differing), "differing": differing}


def _mismatch_message(base, differing):
    """Append a bounded list of the differing paths to a mismatch message."""
    if not differing:
        return base
    shown = differing[:_MAX_MESSAGE_PATHS]
    suffix = ", ".join(shown)
    if len(differing) > len(shown):
        suffix += f" (+{len(differing) - len(shown)} more)"
    return f"{base}; differs at {suffix}"


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
    unknown = sorted(set(config) - set(node_class.model_fields) - {"connection"} - _SCHEDULER_FIELDS - _PRESENTATION_FIELDS)
    if unknown:
        # Name the keys: a builder that wrote `fields: ["price"]` on a market-data node
        # (dev 5d9961de, 2026-09-25) retried the same config twice on the bare message.
        accepted = sorted(set(node_class.model_fields) - _PRESENTATION_FIELDS - {"id", "type", "name", "description", "position", "category"})
        raise ContractViolation("request", "Unknown recording request fields: " + ", ".join(unknown)
                                + " (" + node_type + " accepts: " + ", ".join(accepted) + ")", "REPLAY_FIXTURE_INVALID")
    result = node.model_dump(mode="json", exclude=_PRESENTATION_FIELDS | _SCHEDULER_FIELDS | {"connection"})
    connection = config.get("connection")
    if connection is not None:
        allowed = ("provider", "product", "paper_trading", "broker_node_id", "credential_id")
        if not isinstance(connection, dict):
            raise ContractViolation("request.connection", f"expected object, got {type(connection).__name__}",
                "REPLAY_FIXTURE_INVALID", {"key": "connection", "expected": "object",
                "received_type": type(connection).__name__, "allowed_keys": list(allowed)})
        # A null-valued identity key is semantically absent: at replay the engine
        # injects an unlinked broker's identity WITHOUT a credential_id key at all,
        # so a recorded {credential_id: null, ...} must equal that same identity.
        # Drop None on this (and the recorded) side before validation and hashing.
        cleaned = {key: value for key, value in connection.items() if value is not None}
        unknown = sorted(set(cleaned) - set(allowed))
        if unknown:
            raise ContractViolation(f"request.connection.{unknown[0]}",
                "key(s) not in the non-secret broker identity allowlist: " + ", ".join(unknown),
                "REPLAY_FIXTURE_INVALID", {"key": unknown[0], "expected": "one of " + ", ".join(allowed),
                "received_type": type(cleaned[unknown[0]]).__name__, "allowed_keys": list(allowed),
                "unknown_keys": unknown})
        for key, value in cleaned.items():
            expected = "bool" if key == "paper_trading" else "nonempty string"
            valid = type(value) is bool if key == "paper_trading" else (isinstance(value, str) and bool(value))
            if not valid:
                raise ContractViolation(f"request.connection.{key}",
                    f"expected {expected}, got {type(value).__name__}", "REPLAY_FIXTURE_INVALID",
                    {"key": key, "expected": expected, "received_type": type(value).__name__,
                     "allowed_keys": list(allowed)})
        if cleaned:
            result["connection"] = cleaned
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


def source_recording(node_type, config, source, contract, *, as_of, item=None):
    """Bind raw I/O inputs; the native parser still computes the node output."""
    result = recording(node_type, config, source, contract, as_of=as_of, item=item)
    result["kind"] = "raw_source"
    result["source"] = result.pop("output")
    result["source_contract"] = result.pop("contract")
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
    resolved = request_identity(node_type, config)
    if content_hash(record["request"]) != content_hash(resolved):
        # The recorded request is already public to the model (build guidance
        # exposes it) and holds only non-secret identity, so a field-level diff
        # is precise diagnostics, not an oracle leak.
        detail = mismatch_detail(record["request"], resolved)
        raise ContractViolation(node_id, _mismatch_message(
            "Recording does not match the resolved node request", detail["differing"]),
            "REPLAY_FIXTURE_MISMATCH", detail)
    if not context.validation_as_of or record["as_of"] != context.validation_as_of:
        detail = {"recorded": {"as_of": record["as_of"]},
                  "resolved": {"as_of": context.validation_as_of}, "differing": ["as_of"]}
        raise ContractViolation(node_id, _mismatch_message(
            "Recording does not match the shared replay clock", ["as_of"]),
            "REPLAY_FIXTURE_MISMATCH", detail)
    item = context._iteration_item if context._iteration_total else None
    if content_hash(record["item"]) != content_hash(item):
        detail = mismatch_detail(record["item"], item)
        raise ContractViolation(node_id, _mismatch_message(
            "Recording does not match the actual iteration item", detail["differing"]),
            "REPLAY_FIXTURE_MISMATCH", detail)
    return record
