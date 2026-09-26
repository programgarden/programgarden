"""Machine-readable per-node execution/replay semantics, derived from contract code.

Metadata only. This module adds NO behaviour to any node or replay path; it reads
the engine's own single-source-of-truth contract sets and executor tables and
projects them into a compact block the AI service (designer / Jev judge /
compiler) and the node catalog can consume without re-deriving engine semantics
from prose. Because every value is derived from the same sets the runtime uses,
the block cannot drift (a unit test cross-checks the derivation against those
sets).

Closed value sets follow the design vocabulary exactly (so consumers can switch
on them):

    role      : external | source | broker | order | trigger | gate |
                clock_gate | computation | sink
    replay.recording : required | forbidden | orders_response_only
    output-port shape: signal | any | array<row> | object<row> |
                       symbol_keyed<bar[]> | row<time_series> | array<order> |
                       object<connection>

Grounding (paths relative to src/programgarden/programgarden unless noted):
  - FIXTURE_NODES / COMPUTATION_NODES / _RESERVED_OUTPUT_KEYS : validation_replay.py:26-56
  - SOURCE_NODES                                              : replay_sources.py:13
  - ORDER_NODES + market-buy->limit conversion               : replay_order_adapter.py:15-17,151-165
  - subsequent_event_types (emits_events)                    : replay_events.py:43-62
  - schedule tick == next cron instant / limits / disabled   : replay_events.py:110-133
  - schedule_startup (executes-once {trigger:true}, tz/limit): replay_triggers.py:43-60
  - SessionGate evaluate_at / TradingHours wait-blocks-replay: validation_replay.py:276-289; replay_triggers.py:62-71
  - request_identity (own fields, connection allowlist)      : replay_external.py:94-146
  - per-item recording key EXCHANGE:SYMBOL (KRX default)     : replay_external.py:178-190
  - connection auto-injection (product-scoped nodes)         : executor.py:23582-23641 (WorkflowJob)
  - auto-iteration eligibility (NO_AUTO_ITERATE_NODE_TYPES)  : executor.py:22319-22343 (WorkflowJob)
  - SIM-<node> / SIM-REPLACE-<node> order ids                : replay_orders.py:134,236,338-343
  - order rejection reasons / futures-only held refusal      : replay_orders.py:95-133
  - ThrottleNode interval_sec upper bound (<=300)            : core .../nodes/infra.py:196-199,348
  - TradingHoursFilter default window (US regular)           : core .../nodes/trigger.py:268-271
  - ScheduleNode field defaults (cron/tz/enabled/limits)     : core .../nodes/trigger.py:45-66; replay_events.py:119-127
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional


# --- non-secret broker identity allowlist (replay_external.py:119) -----------
# The engine allows exactly these keys in request.connection. `credential_id` is
# present only when the account is linked; it is marked "?" here as optional.
_CONNECTION_KEYS: List[str] = [
    "provider", "product", "paper_trading", "broker_node_id", "credential_id?",
]
# Fields a recorded request may NOT carry: `product` is not a broker request
# field (it lives inside connection), `credential_ref` is not in the allowlist,
# and a null-valued identity key is dropped before matching (replay_external.py:
# 114-142). Names are descriptive labels, not literal engine tokens.
_REQUEST_FORBIDDEN: List[str] = ["product", "credential_ref", "null_identity"]

_REAL_TRIGGER_SUFFIXES = ("RealMarketDataNode", "RealOrderEventNode", "RealAccountNode")


@lru_cache(maxsize=1)
def _contract():
    """Load the engine's single-source-of-truth contract sets and tables (lazy).

    Imported inside the function so importing this module (e.g. from the tool
    registry) does not eagerly pull the executor for callers that never derive a
    block. Cached so per-type derivation pays the import cost once.
    """
    from programgarden_core import NodeTypeRegistry
    from programgarden_core.nodes.base import BaseNode
    from programgarden.validation_replay import (
        FIXTURE_NODES, COMPUTATION_NODES, _RESERVED_OUTPUT_KEYS,
    )
    from programgarden.replay_sources import SOURCE_NODES
    from programgarden.replay_order_adapter import ORDER_NODES
    from programgarden.replay_events import subsequent_event_types
    from programgarden.executor import WorkflowJob

    return {
        "registry": NodeTypeRegistry(),
        "base_fields": frozenset(BaseNode.model_fields),
        "FIXTURE": FIXTURE_NODES,
        "SOURCE": SOURCE_NODES,
        "COMPUTATION": COMPUTATION_NODES,
        "ORDER": ORDER_NODES,
        "reserved_keys": tuple(_RESERVED_OUTPUT_KEYS),
        "subsequent_event_types": subsequent_event_types,
        "no_auto_iterate": frozenset(WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES),
    }


# ---------------------------------------------------------------------------
# Product-level execution facts (venue / currency / market hours). Kept as a
# sibling map so ~10 product-scoped nodes per product reference it instead of
# repeating it. Market hours: only the US regular window is defined in engine
# CODE (TradingHoursFilterNode defaults, core .../nodes/trigger.py:268-271); KRX
# regular hours are stated as a public fact (not in engine code); the Korean
# daytime (Blue Ocean) session for overseas stocks and overseas-futures hours
# are NOT defined in code (owner facts / contract-specific) and are left null.
# ---------------------------------------------------------------------------
def product_execution() -> Dict[str, Dict[str, Any]]:
    """Per-product execution facts keyed by product_scope.

    Each entry: {tz, currency, sessions (names), venue, session_hours}. A
    session_hours entry with open/close null is a session that trades but whose
    window is not defined in engine code (noted in `note`).
    """
    return {
        "overseas_stock": {
            "tz": "America/New_York",
            "currency": "USD",
            # Owner 2026-09-25: US stocks trade from the KR account in BOTH the
            # Korean daytime session and the US regular session.
            "sessions": ["kr_daytime", "us_regular"],
            "venue": None,  # US venues (NASDAQ/NYSE/AMEX); no single venue token
            "session_hours": {
                # engine: TradingHoursFilterNode defaults 09:30-16:00 ET; public
                "us_regular": {"open": "09:30", "close": "16:00",
                               "tz": "America/New_York",
                               "source": "engine:TradingHoursFilterNode defaults + public"},
                # tradable (owner) but the window is not defined in engine code
                "kr_daytime": {"open": None, "close": None, "tz": "Asia/Seoul",
                               "note": "Korean daytime (Blue Ocean) session for US "
                                       "stocks; tradable per owner 2026-09-25, window "
                                       "not defined in engine code"},
            },
        },
        "korea_stock": {
            "tz": "Asia/Seoul",
            "currency": "KRW",
            "sessions": ["krx_regular"],
            "venue": "KRX",
            "session_hours": {
                # public fact (KRX); not defined as a constant in engine code
                "krx_regular": {"open": "09:00", "close": "15:30", "tz": "Asia/Seoul",
                                "source": "public (KRX); not in engine code"},
            },
        },
        "overseas_futures": {
            # Not provable from code: futures hours/venue/tz vary per contract.
            "tz": None,
            "currency": None,
            "sessions": ["contract_specific"],
            "venue": None,
            "session_hours": {
                "contract_specific": {"open": None, "close": None,
                                      "note": "overseas futures hours vary per "
                                              "contract; not defined in engine code"},
            },
        },
    }


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------
def _role(node_type: str, category: Optional[str], c) -> str:
    # ScheduleNode/StartNode/*Real* are triggers even though the two *Real* kinds
    # are also FIXTURE recording nodes (design vocab: trigger wins). See
    # subsequent_event_types (replay_events.py:43-62) and executor scheduler.
    if node_type in ("ScheduleNode", "StartNode"):
        return "trigger"
    if node_type.endswith(_REAL_TRIGGER_SUFFIXES):
        return "trigger"
    # Immediate time gates evaluated at the fixture instant (validation_replay.py
    # :276-289) — distinct from a boolean data gate.
    if node_type in ("SessionGateNode", "TradingHoursFilterNode"):
        return "clock_gate"
    if node_type == "IfNode":
        return "gate"
    if node_type.endswith("BrokerNode") and node_type in c["FIXTURE"]:
        return "broker"
    if node_type in c["ORDER"]:
        return "order"
    if node_type in c["FIXTURE"]:
        return "external"
    if node_type in c["SOURCE"]:
        return "source"
    if category == "display":
        return "sink"
    # COMPUTATION_NODES and the execute-without-recording remainder (SQLiteNode).
    return "computation"


def _recording(node_type: str, c) -> str:
    """Closed set: required | forbidden | orders_response_only.

    Consumer contract (2026-09-25): the compiler's per-frame recording rule reads
    recording == "required" to decide which nodes need a recording in every tick
    frame. Every FIXTURE_NODES member — brokers included — is re-recorded per
    tick, so brokers are "required", not a weaker "metadata_only". Sources are
    also required (in raw_source form). Only the execute-without-recording nodes
    (COMPUTATION + StartNode/ScheduleNode/gates/SQLite/display) are "forbidden".
    Grounding: validation_replay.py:238 (FIXTURE->external_record required),
    :265 (SOURCE->source_record), :293 (COMPUTATION execute); order nodes go
    through the order adapter (replay_order_adapter.py:167).
    """
    if node_type in c["ORDER"]:
        return "orders_response_only"
    if node_type in c["FIXTURE"] or node_type in c["SOURCE"]:
        return "required"
    return "forbidden"


def _own_fields(node_class, c) -> List[str]:
    """Config fields the node adds on top of BaseNode, minus the injected
    `connection` (tracked under request.injected). request_identity allows
    exactly model_fields minus presentation/scheduler minus connection
    (replay_external.py:114); presentation/scheduler fields live on BaseNode and
    so are already excluded by the set difference."""
    return sorted(set(node_class.model_fields) - c["base_fields"] - {"connection"})


def _port_shape(node_type: str, role: str, port_name: str, port_type: str) -> Optional[str]:
    """Map an engine output-port type to the closed shape vocabulary, or None to
    omit a scalar port that has no structural shape. Node/port context resolves
    the two ohlcv_data envelopes (realtime symbol-keyed vs historical row) and the
    NewOrder result array."""
    if port_type == "signal":
        return "signal"
    # A broker/LLM connection handle injected downstream (broker.py:44-55;
    # LLMModelNode `connection: ai_model`).
    if port_type in ("broker_connection", "ai_model"):
        return "object<connection>"
    if port_type == "ohlcv_data":
        # *RealMarketDataNode records ohlcv_data (and its data alias) as a
        # symbol-keyed dict of bar lists; a *HistoricalDataNode `value` is one row
        # {symbol, exchange, time_series:[bars]}; historical `values` is the array
        # of such rows.
        if node_type.endswith("RealMarketDataNode"):
            return "symbol_keyed<bar[]>"
        if node_type.endswith("HistoricalDataNode") and port_name == "value":
            return "row<time_series>"
        return "array<row>"
    # A NewOrder `result` port is an ARRAY of one order object (replay_order_
    # adapter.py:191); open_orders / rebalance_orders (order_list) are arrays too.
    if role == "order" and port_name == "result":
        return "array<order>"
    if port_type == "order_list":
        return "array<order>"
    if port_type in ("array", "symbol_list", "trade_list"):
        return "array<row>"
    if port_type in ("object", "dict", "balance_data", "position_data",
                     "fundamental_data", "portfolio_result", "performance_summary",
                     "order_result", "order", "order_event"):
        return "object<row>"
    if port_type == "any":
        return "any"
    # string / number / integer / bool / boolean — scalar, no structural shape.
    return None


def _output_ports(node_type: str, role: str, outputs) -> tuple[Dict[str, str], List[str]]:
    ports: Dict[str, str] = {}
    internal: List[str] = []
    for port in outputs:
        name, ptype = port.get("name"), port.get("type")
        if not name:
            continue
        # `_`-prefixed ports never trigger downstream (ThrottleNode _throttle_stats;
        # executor throttle branch) — surfaced separately, not as data ports.
        if name.startswith("_"):
            internal.append(name)
            continue
        shape = _port_shape(node_type, role, name, ptype)
        if shape is not None:
            ports[name] = shape
    return ports, sorted(internal)


def _iterates(node_type: str, role: str, c, own_fields: List[str]) -> Optional[Dict[str, Any]]:
    """Per-item auto-iteration block for recording nodes that fan out over an
    upstream symbol array. Eligibility: a FIXTURE/SOURCE node that is not in
    NO_AUTO_ITERATE_NODE_TYPES (executor.py:22319), is not a broker (broker
    output is connection metadata, item=null), and consumes a `symbols` batch
    field. The per-item recording key is EXCHANGE:SYMBOL, and KoreaStock* defaults
    the exchange to KRX (replay_external.py:178-190)."""
    if node_type not in c["FIXTURE"] and node_type not in c["SOURCE"]:
        return None
    if node_type in c["no_auto_iterate"] or role == "broker":
        return None
    if "symbols" not in own_fields:
        return None
    block: Dict[str, Any] = {
        "mode": "per_item",
        "item": "{exchange,symbol}",
        "when": "upstream_array_or_symbols_list",
        "record_key": "EXCHANGE:SYMBOL",
        "single": "item=null",
    }
    if node_type.startswith("KoreaStock"):
        block["default_exchange"] = "KRX"
    return block


def _on_event(node_type: str) -> Optional[Dict[str, Any]]:
    """Trigger-only. ScheduleNode re-runs the whole main flow on a tick
    (executor _event_loop schedule_tick -> _execute_main_flow), so it re-runs
    itself and every downstream node; a streaming *Real* trigger re-runs only its
    downstream chain (_handle_realtime_update -> _find_downstream_nodes), so the
    startup account/open-order snapshots are retained. Both re-record every
    external node in the frame per replay_events.event_fixture (:64-79)."""
    if node_type == "ScheduleNode":
        return {"reruns": "self_and_every_downstream",
                "external_downstream": "recording_per_frame",
                "upstream_outputs": "retained", "book": "cumulative"}
    if node_type.endswith(_REAL_TRIGGER_SUFFIXES):
        return {"reruns": "listed_only",
                "external_downstream": "recording_per_frame",
                "upstream_outputs": "retained", "book": "cumulative"}
    return None


def _order_block(node_type: str, product_scope: str, own_fields: List[str]) -> Dict[str, Any]:
    """ORDER_NODES only. Grounding in replay_orders.py / replay_order_adapter.py."""
    # config_keys = the node's own order parameters (connection is injected,
    # resilience is a retry policy, neither is an order intent field).
    config_keys = [f for f in own_fields if f not in ("connection", "resilience")]
    block: Dict[str, Any] = {"config_keys": config_keys}
    if node_type.endswith("NewOrderNode"):
        # replay_orders.py:134 SIM-<node_id> (#2.. on repeats).
        block["sim_id"] = "SIM-<node_id>"
        block["result_shape"] = "array<order>"          # replay_order_adapter.py:191
        block["one_active_order_per_symbol"] = True      # pending_or_unknown_order (:117)
        # Stocks have NO held-symbol refusal; only futures adding to an open
        # same-direction position is refused (replay_orders.py:129).
        block["held_symbol_refusal"] = (product_scope == "overseas_futures")
        if product_scope == "overseas_stock":
            # overseas-stock market BUY submits as a LIMIT at the quote
            # (replay_order_adapter.py:162-165; executor.py:16377-16399).
            block["market_buy"] = "limit_at_quote"
    elif node_type.endswith("ModifyOrderNode"):
        block["sim_id"] = "SIM-REPLACE-<node_id>"        # replay_orders.py:236
        # A modify/cancel is only acknowledged in-tick; completion is expressed by
        # a downstream *OpenOrdersNode recording's top-level order_events.
        block["acknowledged_only"] = True
    elif node_type.endswith("CancelOrderNode"):
        block["acknowledged_only"] = True
    return block


def _time_rules(node_type: str, role: str) -> List[Dict[str, Any]]:
    """Closed rule ids; each entry is an object with an `id`."""
    if node_type == "ScheduleNode":
        # replay_events.py:110-133 + replay_triggers.py:43-60 + core trigger.py:45-66.
        return [
            {"id": "cron_required", "field": "cron", "format": "5-field", "default": None},
            {"id": "tick_next_cron_instant", "granularity": "minute",
             "after": "prior_frame", "min_gap_s": 60},
            {"id": "timezone_iana", "field": "timezone",
             "default": "America/New_York", "invalid": "replay_rejects"},
            {"id": "disabled_emits_nothing", "field": "enabled"},
            {"id": "limits", "optional": True, "absent_means": "unbounded",
             "count": {"default": None, "min": 1},
             "max_duration_hours": {"default": None, "gt": 0}, "pin": "range_not_const"},
        ]
    if node_type == "SessionGateNode":
        return [{"id": "evaluate_at_fixture_instant"}]   # validation_replay.py:276-283
    if node_type == "TradingHoursFilterNode":
        return [{"id": "wait_blocks_replay"}]            # replay_triggers.py:62-71
    if node_type == "ThrottleNode":
        return [{"id": "interval_max_s", "value": 300}]  # core infra.py:196-199,348
    if role in ("external", "source"):
        # An external recording is a snapshot bound to the fixture instant
        # (replay_external.py:203-208 as_of match).
        return [{"id": "snapshot_at_call_time"}]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def execution_for(node_type: str) -> Optional[Dict[str, Any]]:
    """Derive the execution-semantics block for a registered node type.

    Returns None for an unregistered type. Every key is traceable to the contract
    code cited in this module's docstring; a key is omitted rather than guessed.
    """
    c = _contract()
    node_class = c["registry"].get(node_type)
    if node_class is None:
        return None
    schema = c["registry"].get_schema(node_type)  # raw (no locale); ports carry type
    if schema is None:
        return None

    category = schema.category
    product_scope = schema.product_scope or "all"
    role = _role(node_type, category, c)
    recording = _recording(node_type, c)
    own_fields = _own_fields(node_class, c)
    ports, internal_ports = _output_ports(node_type, role, schema.outputs or [])
    emits = sorted(c["subsequent_event_types"](node_type))

    block: Dict[str, Any] = {"role": role}

    # --- replay --------------------------------------------------------------
    replay: Dict[str, Any] = {"recording": recording}
    if recording == "required":
        replay["form"] = "raw_source" if node_type in c["SOURCE"] else "output"
        if ports:
            replay["envelope"] = dict(ports)
    if node_type == "ScheduleNode":
        # schedule_startup returns the live executor's {trigger: True} once
        # (replay_triggers.py:43-60).
        replay["startup"] = "executes_once:{trigger:true}"
    block["replay"] = replay

    # --- request -------------------------------------------------------------
    if recording == "required":
        request: Dict[str, Any] = {"own_fields": own_fields}
        if role == "broker":
            # A broker's own recorded request never carries a connection; it
            # CREATES the connection metadata (replay_external.py:116-146 excludes
            # connection from the broker's identity on the first run).
            request["never_connection"] = True
        elif product_scope != "all":
            # The engine resolves this node's request WITH the upstream broker's
            # identity (executor.py:23582-23641; replay_external.py:117-146).
            request["injected"] = {"connection": "upstream_broker_identity"}
            request["connection_keys"] = list(_CONNECTION_KEYS)
            request["forbidden"] = list(_REQUEST_FORBIDDEN)
        else:
            request["injected"] = {}
        block["request"] = request
    else:
        block["request"] = None

    # --- iteration -----------------------------------------------------------
    block["iteration"] = _iterates(node_type, role, c, own_fields)

    # --- rerun / events ------------------------------------------------------
    # A trigger is the source of re-runs; a non-trigger node re-runs when placed
    # downstream of a schedule tick (executor _event_loop re-runs the main flow)
    # and when its trigger input fires.
    block["reruns_on"] = [] if role == "trigger" else [
        "downstream_of:schedule_tick", "input:trigger"]
    block["emits_events"] = emits
    on_event = _on_event(node_type)
    if on_event is not None:
        block["on_event"] = on_event

    # --- ports ---------------------------------------------------------------
    block["output_ports"] = ports
    # No declared port is provably never-emitted in this engine version, so the
    # dead-port list is empty (kept for shape stability; never guessed).
    block["dead_ports"] = []
    if internal_ports:
        block["internal_ports"] = internal_ports
    # error/reason are reserved for COMPUTATION nodes (validation_replay.py:309-315
    # fails on a top-level `error` key or an invalid-input `reason` there).
    block["reserved_output_ports"] = (
        list(c["reserved_keys"]) if node_type in c["COMPUTATION"] else [])

    # --- gating --------------------------------------------------------------
    if node_type == "IfNode":
        # A native IfNode evaluates exactly one left/operator/right comparison;
        # the untaken `false` port skips its branch (executor _compute_if_skip).
        block["gating"] = {"false_path": "false", "single_comparison": True}
    elif node_type == "CodeNode":
        # A CodeNode returning a boolean false skips nothing — route through IfNode.
        block["gating"] = {"boolean_completion_is_not_a_gate": True}

    # --- order ---------------------------------------------------------------
    if node_type in c["ORDER"]:
        block["order"] = _order_block(node_type, product_scope, own_fields)

    # --- time rules ----------------------------------------------------------
    time_rules = _time_rules(node_type, role)
    if time_rules:
        block["time_rules"] = time_rules

    # --- venue (product map) -------------------------------------------------
    # Every product-scoped node carries the product's execution facts (tz /
    # currency / session hours) under `venue`; `all`-scoped nodes have no venue.
    if product_scope != "all":
        block["venue"] = product_execution().get(product_scope)

    return block


def _fmt_hours(session: str, hours: Dict[str, Any]) -> str:
    open_, close = hours.get("open"), hours.get("close")
    tz = hours.get("tz")
    if open_ and close:
        return f"- {session}: {open_}-{close} {tz}."
    note = hours.get("note") or "window not defined in engine code"
    return f"- {session}: {note}."


def execution_semantics_text(node_type: str) -> List[str]:
    """Render the execution block into short English bullet sentences (one fact
    per line), suitable for appending to a node's `features` for the chatbot
    catalog. Deterministic, no adjectives."""
    block = execution_for(node_type)
    if not block:
        return []
    lines: List[str] = []
    role = block["role"]
    lines.append(f"Role: {role}.")

    recording = block["replay"]["recording"]
    if recording == "required":
        form = block["replay"].get("form", "output")
        lines.append(f"Replay recording: required (form {form}); it is re-recorded "
                     "in every tick frame it executes in.")
    elif recording == "orders_response_only":
        lines.append("Replay recording: an explicit order-response scenario is "
                     "required; the node has no output recording.")
    else:
        lines.append("Replay recording: forbidden; the node executes in replay.")

    req = block.get("request")
    if isinstance(req, dict):
        if req.get("own_fields"):
            lines.append("Recording request carries only these native fields: "
                         + ", ".join(req["own_fields"]) + ".")
        if req.get("never_connection"):
            lines.append("Its own request never carries a connection; it creates "
                         "the connection metadata for downstream nodes.")
        if req.get("injected", {}).get("connection"):
            lines.append("The upstream broker connection is injected into the "
                         "request (identity keys: " + ", ".join(_CONNECTION_KEYS) + ").")

    it = block.get("iteration")
    if isinstance(it, dict):
        line = ("Auto-iterates per item over an upstream symbol array; each per-item "
                "recording is keyed EXCHANGE:SYMBOL and a single non-iterated "
                "recording sets item=null.")
        if it.get("default_exchange"):
            line = line[:-1] + " (exchange defaults to KRX when omitted)."
        lines.append(line)

    emits = block.get("emits_events") or []
    if emits:
        lines.append("Emits subsequent events: " + ", ".join(emits) + ".")
    else:
        lines.append("Emits no subsequent event.")

    oe = block.get("on_event")
    if isinstance(oe, dict):
        if oe.get("reruns") == "self_and_every_downstream":
            lines.append("On each tick it re-runs itself and every downstream node; "
                         "each external downstream node needs a fresh per-frame "
                         "recording; startup snapshots are retained; the order book "
                         "is cumulative.")
        else:
            lines.append("On each event it re-runs only its downstream chain; "
                         "startup account/open-order snapshots are retained; the "
                         "order book is cumulative.")

    if block.get("output_ports"):
        lines.append("Output ports: " + ", ".join(
            f"{name} ({shape})" for name, shape in block["output_ports"].items()) + ".")
    if block.get("internal_ports"):
        lines.append("Internal ports never trigger downstream: "
                     + ", ".join(block["internal_ports"]) + ".")
    if block.get("reserved_output_ports"):
        lines.append("Reserved output keys (never declare or expect): "
                     + ", ".join(block["reserved_output_ports"]) + ".")

    gating = block.get("gating")
    if isinstance(gating, dict):
        if node_type == "IfNode":
            lines.append("Evaluates exactly one left/operator/right comparison; the "
                         "false port skips its branch.")
        elif node_type == "CodeNode":
            lines.append("A boolean completion is not a gate; route a branch "
                         "decision through an IfNode.")

    order = block.get("order")
    if isinstance(order, dict):
        if order.get("result_shape"):
            lines.append("Booked as " + order["sim_id"] + "; the result port is an "
                         "array of one order object.")
        if order.get("market_buy") == "limit_at_quote":
            lines.append("An overseas-stock market BUY is submitted as a LIMIT order "
                         "at the current quote.")
        if order.get("acknowledged_only"):
            lines.append("A modify/cancel is only acknowledged in-tick; its "
                         "completion is a downstream OpenOrders order_events entry.")
        if order.get("one_active_order_per_symbol"):
            lines.append("At most one active order per symbol at a time.")

    tr_ids = {r.get("id") for r in block.get("time_rules", [])}
    if "snapshot_at_call_time" in tr_ids:
        lines.append("Its recorded output is a snapshot at the fixture instant.")
    if "evaluate_at_fixture_instant" in tr_ids:
        lines.append("The decision is a pure function of the fixture instant and "
                     "config; two frames at the same instant get the same result.")
    if "wait_blocks_replay" in tr_ids:
        lines.append("Live it waits outside the window; in replay an out-of-window "
                     "instant is refused, so only in-window instants replay.")
    if "interval_max_s" in tr_ids:
        lines.append("Cooldown state persists across re-triggers; interval_sec is at "
                     "most 300 and must be pinned as a range, never a const.")

    if "cron_required" in tr_ids:
        _schedule_time_lines(lines)

    return lines


def _schedule_time_lines(lines: List[str]) -> None:
    """ScheduleNode-specific bullets: cron/tick rules + market operating hours +
    the market-relative time rule (owner 2026-09-25)."""
    lines.append("cron is required (5-field); the timezone defaults to "
                 "America/New_York; a disabled schedule emits no tick.")
    lines.append("A recorded tick must equal the cron's next firing instant after "
                 "the prior frame in this timezone: a whole minute, at least one "
                 "minute later.")
    lines.append("count and max_duration_hours are optional safety limits; omit both "
                 "and the schedule runs until the workflow is stopped. When provided, "
                 "count must be >= 1 and max_duration_hours > 0, and a contract bounds "
                 "them with a range, never a const.")
    lines.append("Set the cron time in the target market's timezone. Market "
                 "operating hours by product:")
    pe = product_execution()
    for scope in ("korea_stock", "overseas_stock", "overseas_futures"):
        entry = pe.get(scope, {})
        for session in entry.get("sessions", []):
            hours = entry.get("session_hours", {}).get(session, {})
            lines.append(_fmt_hours(f"{scope} / {session}", hours))
    lines.append("A time stated relative to a market ('장 열리고 30분 뒤' = 30 minutes "
                 "after the open) is that many minutes AFTER that market's open in "
                 "its timezone: US open 09:30 + 30 = 10:00 America/New_York; cron "
                 "'0 10 * * 1-5'.")


def attach_execution(schema):
    """Return a COPY of a NodeTypeSchema carrying the derived `execution` block
    and its rendered lines merged into `features` (without duplicating existing
    lines). Never mutates the registry's cached schema instance.

    Used by the tool registry (list_node_types / get_node_schema) so served
    schemas carry execution semantics; the core registry itself leaves the field
    None (core must not import programgarden).
    """
    block = execution_for(schema.node_type)
    if block is None:
        return schema
    features = list(schema.features or [])
    for line in execution_semantics_text(schema.node_type):
        if line not in features:
            features.append(line)
    return schema.model_copy(update={"execution": block, "features": features})
