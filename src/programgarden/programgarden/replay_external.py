"""Explicit external recordings with per-item identity and no transport."""

from programgarden.replay_contracts import ContractViolation


def external_record(fixture, node_id, node_type, context):
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
    return record
