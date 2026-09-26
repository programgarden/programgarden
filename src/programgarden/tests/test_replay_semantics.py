"""Execution-semantics blocks are derived from the contract sets, never per class.

Cross-checks the derivation in ``programgarden.replay_semantics`` against the same
single-source-of-truth sets the runtime uses (FIXTURE_NODES / SOURCE_NODES /
ORDER_NODES / COMPUTATION_NODES / subsequent_event_types), pins the grounded
examples from the design, and confirms the tool registry serves the block.
"""
import pytest

from programgarden_core import NodeTypeRegistry
from programgarden.replay_semantics import (
    execution_for, execution_semantics_text, product_execution, attach_execution,
)
from programgarden.validation_replay import FIXTURE_NODES, COMPUTATION_NODES
from programgarden.replay_sources import SOURCE_NODES
from programgarden.replay_order_adapter import ORDER_NODES
from programgarden.replay_events import subsequent_event_types
from programgarden.tools.registry_tools import list_node_types, get_node_schema

VALID_ROLES = {"external", "source", "broker", "order", "trigger", "gate",
               "clock_gate", "computation", "sink"}
_REAL = ("RealMarketDataNode", "RealOrderEventNode", "RealAccountNode")

REGISTERED = sorted(NodeTypeRegistry().list_types())


def test_every_registered_type_has_a_block_with_a_valid_role():
    assert REGISTERED, "registry is empty"
    for node_type in REGISTERED:
        block = execution_for(node_type)
        assert block is not None, f"{node_type} has no execution block"
        assert block["role"] in VALID_ROLES, f"{node_type} role {block['role']!r}"


def test_unregistered_type_returns_none():
    assert execution_for("NoSuchNode") is None
    assert execution_semantics_text("NoSuchNode") == []


@pytest.mark.parametrize("node_type", REGISTERED)
def test_roles_agree_with_contract_sets(node_type):
    role = execution_for(node_type)["role"]
    if node_type in ORDER_NODES:
        assert role == "order"
    elif node_type in ("ScheduleNode", "StartNode") or node_type.endswith(_REAL):
        assert role == "trigger"
    elif node_type in ("SessionGateNode", "TradingHoursFilterNode"):
        assert role == "clock_gate"
    elif node_type == "IfNode":
        assert role == "gate"
    elif node_type.endswith("BrokerNode") and node_type in FIXTURE_NODES:
        assert role == "broker"
    elif node_type in FIXTURE_NODES:
        assert role == "external"
    elif node_type in SOURCE_NODES:
        assert role == "source"
    elif node_type in COMPUTATION_NODES:
        # display nodes are sinks; the rest are computation
        assert role in ("computation", "sink")
    else:
        # execute-without-recording remainder (e.g. SQLiteNode)
        assert role == "computation"


@pytest.mark.parametrize("node_type", REGISTERED)
def test_recording_agrees_with_contract_sets(node_type):
    recording = execution_for(node_type)["replay"]["recording"]
    if node_type in ORDER_NODES:
        assert recording == "orders_response_only"
    elif node_type in FIXTURE_NODES or node_type in SOURCE_NODES:
        assert recording == "required"
    else:
        assert recording == "forbidden"
    assert recording in {"required", "forbidden", "orders_response_only"}


@pytest.mark.parametrize("node_type", REGISTERED)
def test_emits_events_equals_subsequent_event_types(node_type):
    assert execution_for(node_type)["emits_events"] == sorted(subsequent_event_types(node_type))


@pytest.mark.parametrize("node_type", REGISTERED)
def test_source_nodes_record_as_raw_source(node_type):
    if node_type in SOURCE_NODES:
        assert execution_for(node_type)["replay"]["form"] == "raw_source"


def test_fixture_nodes_record_as_output_form_including_brokers():
    # The compiler's per-frame rule keys on recording == "required"; brokers must
    # not drop out of it, so they are "required" with output form.
    for node_type in FIXTURE_NODES:
        replay = execution_for(node_type)["replay"]
        assert replay["recording"] == "required"
        assert replay["form"] == "output"
    broker = execution_for("OverseasStockBrokerNode")
    assert broker["replay"]["envelope"] == {"connection": "object<connection>"}


# --- grounded examples from the design file --------------------------------
def test_schedule_node_matches_grounded_example():
    b = execution_for("ScheduleNode")
    assert b["role"] == "trigger"
    assert b["replay"] == {"recording": "forbidden",
                           "startup": "executes_once:{trigger:true}"}
    assert b["request"] is None
    assert b["iteration"] is None
    assert b["reruns_on"] == []
    assert b["emits_events"] == ["schedule_tick"]
    assert b["on_event"] == {"reruns": "self_and_every_downstream",
                             "external_downstream": "recording_per_frame",
                             "upstream_outputs": "retained", "book": "cumulative"}
    assert b["output_ports"] == {"trigger": "signal"}
    assert b["dead_ports"] == []
    assert b["reserved_output_ports"] == []
    ids = {r["id"] for r in b["time_rules"]}
    assert ids == {"cron_required", "tick_next_cron_instant", "timezone_iana",
                   "disabled_emits_nothing", "limits"}
    tz_rule = next(r for r in b["time_rules"] if r["id"] == "timezone_iana")
    assert tz_rule["default"] == "America/New_York"
    limits = next(r for r in b["time_rules"] if r["id"] == "limits")
    assert limits["pin"] == "range_not_const"
    assert "venue" not in b  # product_scope=all


def test_code_node_matches_grounded_example():
    b = execution_for("CodeNode")
    assert b["role"] == "computation"
    assert b["replay"]["recording"] == "forbidden"
    assert b["request"] is None
    assert b["reserved_output_ports"] == ["error", "reason"]
    assert b["gating"] == {"boolean_completion_is_not_a_gate": True}
    assert b["output_ports"] == {"result": "any"}
    assert b["emits_events"] == []


def test_overseas_stock_market_data_matches_grounded_example():
    b = execution_for("OverseasStockMarketDataNode")
    assert b["role"] == "external"
    assert b["replay"]["recording"] == "required"
    assert b["replay"]["form"] == "output"
    assert b["replay"]["envelope"] == {"values": "array<row>"}
    assert b["request"]["own_fields"] == ["symbol", "symbols"]
    assert b["request"]["injected"] == {"connection": "upstream_broker_identity"}
    assert b["request"]["connection_keys"] == [
        "provider", "product", "paper_trading", "broker_node_id", "credential_id?"]
    assert b["request"]["forbidden"] == ["product", "credential_ref", "null_identity"]
    assert b["iteration"]["mode"] == "per_item"
    assert b["iteration"]["record_key"] == "EXCHANGE:SYMBOL"
    assert b["iteration"]["single"] == "item=null"
    assert "default_exchange" not in b["iteration"]  # overseas, not KoreaStock
    assert b["output_ports"] == {"values": "array<row>"}
    assert b["emits_events"] == []
    assert {r["id"] for r in b["time_rules"]} == {"snapshot_at_call_time"}
    assert b["venue"]["tz"] == "America/New_York"


def test_korea_stock_market_data_defaults_exchange_krx():
    b = execution_for("KoreaStockMarketDataNode")
    assert b["iteration"]["default_exchange"] == "KRX"


def test_overseas_stock_new_order_matches_grounded_example():
    b = execution_for("OverseasStockNewOrderNode")
    assert b["role"] == "order"
    assert b["replay"]["recording"] == "orders_response_only"
    assert b["request"] is None
    assert b["output_ports"] == {"result": "array<order>"}
    order = b["order"]
    assert order["sim_id"] == "SIM-<node_id>"
    assert order["result_shape"] == "array<order>"
    assert order["market_buy"] == "limit_at_quote"
    assert order["held_symbol_refusal"] is False
    assert order["one_active_order_per_symbol"] is True
    assert order["config_keys"] == ["order", "order_type", "price_type", "side"]


def test_overseas_futures_new_order_refuses_held_symbol():
    order = execution_for("OverseasFuturesNewOrderNode")["order"]
    assert order["held_symbol_refusal"] is True  # futures add-to-position refused
    assert "market_buy" not in order              # only overseas_stock converts


def test_modify_and_cancel_are_acknowledged_only():
    modify = execution_for("OverseasStockModifyOrderNode")["order"]
    assert modify["acknowledged_only"] is True
    assert modify["sim_id"] == "SIM-REPLACE-<node_id>"
    cancel = execution_for("OverseasStockCancelOrderNode")["order"]
    assert cancel["acknowledged_only"] is True


def test_overseas_stock_broker_matches_grounded_example():
    b = execution_for("OverseasStockBrokerNode")
    assert b["role"] == "broker"
    assert b["replay"]["recording"] == "required"
    assert b["replay"]["envelope"] == {"connection": "object<connection>"}
    assert b["request"]["never_connection"] is True
    assert b["request"]["own_fields"] == ["credential_id", "paper_trading", "provider"]
    assert "injected" not in b["request"]
    assert b["output_ports"] == {"connection": "object<connection>"}
    assert b["iteration"] is None


def test_realtime_node_is_trigger_and_recording_required():
    b = execution_for("OverseasStockRealMarketDataNode")
    assert b["role"] == "trigger"
    assert b["replay"]["recording"] == "required"
    assert b["emits_events"] == ["market_data", "realtime_update"]
    assert b["on_event"]["reruns"] == "listed_only"
    assert b["output_ports"]["ohlcv_data"] == "symbol_keyed<bar[]>"


def test_throttle_node_internal_ports_and_interval_cap():
    b = execution_for("ThrottleNode")
    assert b["internal_ports"] == ["_throttle_stats"]
    cap = next(r for r in b["time_rules"] if r["id"] == "interval_max_s")
    assert cap["value"] == 300


# --- product_execution -----------------------------------------------------
def test_product_execution_shape_and_hours():
    pe = product_execution()
    assert set(pe) == {"overseas_stock", "korea_stock", "overseas_futures"}
    us = pe["overseas_stock"]
    assert us["tz"] == "America/New_York" and us["currency"] == "USD"
    assert set(us["sessions"]) == {"kr_daytime", "us_regular"}
    assert us["session_hours"]["us_regular"]["open"] == "09:30"
    assert us["session_hours"]["us_regular"]["close"] == "16:00"
    # Korean daytime session tradable but window not in engine code -> null.
    assert us["session_hours"]["kr_daytime"]["open"] is None
    kr = pe["korea_stock"]
    assert kr["tz"] == "Asia/Seoul" and kr["currency"] == "KRW" and kr["venue"] == "KRX"
    assert kr["session_hours"]["krx_regular"]["open"] == "09:00"
    assert kr["session_hours"]["krx_regular"]["close"] == "15:30"
    # Overseas futures hours vary per contract -> null.
    fx = pe["overseas_futures"]
    assert fx["session_hours"]["contract_specific"]["open"] is None


def test_product_scoped_nodes_carry_venue_and_all_scoped_do_not():
    reg = NodeTypeRegistry()
    for node_type in REGISTERED:
        block = execution_for(node_type)
        scope = reg.get_schema(node_type).product_scope or "all"
        if scope == "all":
            assert "venue" not in block, node_type
        else:
            assert block["venue"] == product_execution()[scope], node_type


# --- rendered text ---------------------------------------------------------
@pytest.mark.parametrize("node_type", REGISTERED)
def test_execution_semantics_text_is_nonempty_english(node_type):
    text = execution_semantics_text(node_type)
    assert text and all(isinstance(line, str) and line.strip() for line in text)
    assert any("Role:" in line for line in text)
    # English: every line is ASCII except at most one (the ScheduleNode market-
    # relative rule carries a Korean example phrase from the owner instruction).
    non_ascii = [line for line in text if not line.isascii()]
    assert len(non_ascii) <= 1, f"{node_type}: {non_ascii}"


def test_schedule_text_carries_market_hours_and_relative_rule():
    text = execution_semantics_text("ScheduleNode")
    joined = "\n".join(text)
    assert "09:00-15:30 Asia/Seoul" in joined      # KRX regular
    assert "09:30-16:00 America/New_York" in joined  # US regular
    assert "vary per contract" in joined            # overseas futures
    assert "09:30 + 30 = 10:00" in joined           # market-relative rule
    assert "0 10 * * 1-5" in joined


# --- tool registry integration --------------------------------------------
def test_registry_tools_results_carry_execution():
    listed = list_node_types()
    assert len(listed) == len(REGISTERED)
    assert all(isinstance(n.get("execution"), dict) and n["execution"].get("role")
               for n in listed)
    schema = get_node_schema("OverseasStockMarketDataNode")
    assert schema["execution"]["role"] == "external"
    # rendered lines merged into features without duplicating existing ones.
    features = schema.get("features") or []
    assert any("Role: external." == f for f in features)
    assert len(features) == len(set(features))


def test_core_registry_does_not_populate_execution():
    # The core registry leaves execution None; only attach_execution fills it.
    raw = NodeTypeRegistry().get_schema("ScheduleNode")
    assert raw.execution is None
    attached = attach_execution(raw)
    assert attached.execution is not None and attached.execution["role"] == "trigger"
    # attach returns a copy; the cached schema stays untouched.
    assert NodeTypeRegistry().get_schema("ScheduleNode").execution is None


def test_get_node_schema_localized_still_carries_execution():
    schema = get_node_schema("ScheduleNode", locale="ko")
    assert schema["execution"]["role"] == "trigger"
