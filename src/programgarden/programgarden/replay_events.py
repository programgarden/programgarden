"""Bounded recorded events through the native event loop, with persistent state.

This verifies delivery consequences, not provider websocket availability or wall
clock timer accuracy. Recordings and assertions are private suite inputs. They
cannot reset balances, positions, pending orders, node state or SQLite storage.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from programgarden.context import WorkflowEvent
from programgarden.replay_contracts import ContractViolation, check_contract


def checked_events(fixture):
    events = fixture.get("events", [])
    check_contract(events, {"type": "array", "maxItems": 32, "items": {
        "type": "object", "required": ["as_of", "type", "source_node_id"],
        "additionalProperties": False, "properties": {
            "as_of": {"type": "string", "format": "date-time"},
            "type": {"type": "string", "enum": ["schedule_tick", "realtime_update", "market_data", "order_event"]},
            "source_node_id": {"type": "string", "minLength": 1},
            "nodes": {"type": "object"}, "orders": {"type": "object"},
            "quotes": {"type": "object"}, "expected": {"type": "object"},
            "must_execute": {"type": "array", "items": {"type": "string"}},
            "expected_simulation": {"type": "object"},
        }}}, "events")
    previous = fixture.get("as_of", fixture.get("broker", {}).get("as_of"))
    for event in events:
        if not previous:
            raise ContractViolation("events", "Recurring replay requires an initial clock")
        if instant(event["as_of"]) < instant(previous):
            raise ContractViolation("events", "Recorded events cannot move the shared clock backward")
        previous = event["as_of"]
    return events


def instant(value):
    check_contract(value, {"type": "string", "format": "date-time"}, "event.as_of")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def subsequent_event_types(node_type):
    """Recorded `events`-frame types a trigger node can emit after the initial run.

    Empty when the node cannot re-trigger (a manual StartNode, TradingHoursFilter,
    a one-shot REST node, SQLite, computation, etc.): a subsequent-event
    ("duplicate") scenario is inapplicable to such a blueprint. The AI-side suite
    compiler imports this to decide whether a duplicate scenario applies. Derived
    from the native dispatch in `replay_events` (and ScheduleNode's single-startup
    replay); it is not a live websocket capability promise.
    """
    if node_type == "ScheduleNode":
        return frozenset({"schedule_tick"})
    if node_type.endswith("RealMarketDataNode"):
        return frozenset({"market_data", "realtime_update"})
    if node_type.endswith("RealOrderEventNode"):
        return frozenset({"order_event", "realtime_update"})
    if node_type.endswith("RealAccountNode"):
        return frozenset({"realtime_update"})
    return frozenset()


def event_fixture(fixture, event):
    """Advance external observations without importing mutable account state."""
    frame = {**deepcopy(fixture), "as_of": event["as_of"],
             "nodes": deepcopy(event.get("nodes", {})),
             "orders": deepcopy(event.get("orders", fixture.get("orders", {})))}
    frame.pop("events", None)
    if "broker" in frame:
        frame["broker"]["as_of"] = event["as_of"]
        instruments = frame["broker"]["instruments"]
        for symbol, quote in event.get("quotes", {}).items():
            if symbol not in instruments or not isinstance(quote, dict) or set(quote) - {"price", "as_of", "session_open", "tradeable"}:
                raise ContractViolation("quotes", "Events can update only known instrument quote facts")
            instruments[symbol].update(deepcopy(quote))
    elif event.get("quotes"):
        raise ContractViolation("quotes", "An initial broker fixture is required")
    return frame


async def replay_events(job, runner, fixture, outcome):
    events = checked_events(fixture)
    # Ancestor-only node checks may not yet contain a later event source. Final
    # verification checks all declared events against the complete graph.
    pending = iter((index, event) for index, event in enumerate(events)
                   if event["source_node_id"] in job.workflow.nodes)
    context = job.context
    origin = instant(context.validation_as_of)
    schedule_instants, schedule_counts = {}, {}
    active, offset = None, 0

    def capture():
        if active is None:
            return
        index, event = active
        outcome.events.append({"index": index, "as_of": event["as_of"],
            "type": event["type"], "source_node_id": event["source_node_id"],
            "executed": list(outcome.executed[offset:]),
            "outputs": {node: deepcopy(context.get_all_outputs(node)) for node in job.workflow.nodes},
            "simulation": runner.orders.book.snapshot() if runner.orders else {}})

    async def next_event(timeout=1.0):
        nonlocal active, offset
        capture()
        active = None
        if outcome.errors:
            context.stop()
            return None
        item = next(pending, None)
        if item is None:
            context.stop()
            return None
        index, event = item
        source_id = event["source_node_id"]
        source = job.workflow.nodes[source_id]
        now = instant(event["as_of"])
        if source.node_type == "ScheduleNode":
            if event["type"] != "schedule_tick":
                raise ContractViolation(source_id, "Schedule recordings require schedule_tick")
            from croniter import croniter
            config = job._resolve_config_expressions(dict(source.config), source_id)
            if config.get("enabled", True) is not True:
                raise ContractViolation(source_id, "A disabled schedule cannot emit a tick")
            prior = schedule_instants.get(source_id, origin)
            zone = ZoneInfo(config.get("timezone", "America/New_York"))
            expected = croniter(config["cron"], prior.astimezone(zone), second_at_beginning=True).get_next(datetime)
            if now != expected:
                raise ContractViolation(source_id, "Recorded tick is not the next configured cron instant")
            count = schedule_counts.get(source_id, 0) + 1
            if count > config.get("count", 1000) or (now - origin).total_seconds() > config.get("max_duration_hours", 24.0) * 3600:
                raise ContractViolation(source_id, "Recorded ticks exceed schedule safety limits")
            schedule_instants[source_id], schedule_counts[source_id] = now, count
        else:
            allowed = subsequent_event_types(source.node_type)
            if event["type"] not in allowed:
                emittable = sorted(allowed)
                if emittable:
                    hint = (f"{source.node_type} emits only {', '.join(emittable)} as a subsequent event; "
                            f"the recorded '{event['type']}' is not one of them")
                else:
                    hint = (f"{source.node_type} is a one-time trigger and emits no subsequent events; a "
                            "subsequent-event (duplicate) scenario requires a recurring trigger node "
                            "(ScheduleNode or a realtime stream), so this is a suite specification defect")
                raise ContractViolation(source_id,
                    f"{source.node_type} cannot emit recorded event type '{event['type']}' "
                    f"(emits: {', '.join(emittable) or 'no subsequent events'}); {hint}",
                    detail={"recorded_event_type": event["type"], "node_type": source.node_type,
                            "emittable_event_types": emittable, "hint": hint})
            if source_id not in event.get("nodes", {}):
                raise ContractViolation(source_id, "Event source needs a fresh request-bound recording", "REPLAY_FIXTURE_REQUIRED")
        context.validation_as_of = event["as_of"]
        frame = event_fixture(runner.fixture, event)
        if runner.orders:
            runner.orders.book.as_of = now
            for symbol, quote in event.get("quotes", {}).items():
                runner.orders.book.instruments[symbol].update(deepcopy(quote))
            runner.orders.responses = frame["orders"]
        runner.fixture = frame
        active, offset = item, len(outcome.executed)
        data = None
        if source.node_type != "ScheduleNode":
            config = job._resolve_config_expressions(dict(source.config), source_id)
            config = job._auto_inject_connection(source_id, source, config)
            data = await runner.execute_node(source_id, source.node_type, config, context,
                plugin=source.plugin, fields=source.fields, workflow=job.workflow)
            context._outputs.pop(source_id, None)
            for port, value in data.items():
                context.set_output(source_id, port, deepcopy(value))
        # Let the real scheduler derive downstream targets and ordering.
        return WorkflowEvent(event["type"], source_id, data=data, timestamp=now)

    original_wait = context.wait_for_event
    context.wait_for_event = next_event
    try:
        await job._event_loop()
    finally:
        capture()
        context.wait_for_event = original_wait
