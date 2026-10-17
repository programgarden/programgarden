"""Responders answer the request a node actually resolves at run time.

Telegram texts, AI prompts and futures orderable-quantity queries often bind
values that exist only during the run (a CodeNode price, an order result), so
no recording made beforehand matches them. A responder answers through the
node's real parser and is reported as a scenario assumption.
"""
import socket

import pytest

from programgarden.replay_external import recording
from programgarden.validation_replay import replay

AS_OF = "2026-10-16T14:00:00Z"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("network access during a responder replay")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _code(node_id, outputs):
    body = ", ".join(f"'{k}': {v!r}" for k, v in outputs.items())
    return {"id": node_id, "type": "CodeNode",
            "outputs": [{"name": k, "type": "number" if isinstance(v, (int, float)) else "string"}
                        for k, v in outputs.items()],
            "code": f"def execute(data, params, context):\n return {{{body}}}"}


def _chain(*nodes, extra_edges=()):
    nodes = [{"id": "start", "type": "StartNode"}, *nodes]
    edges = [{"from": a["id"], "to": b["id"]} for a, b in zip(nodes, nodes[1:])]
    return {"id": "responders", "name": "Responders", "nodes": nodes, "edges": [*edges, *extra_edges]}


@pytest.mark.asyncio
async def test_telegram_text_with_a_runtime_value_lands_in_the_outbox_and_is_never_sent():
    from unittest.mock import patch
    from programgarden_community.nodes.messaging.telegram import TelegramNode
    graph = _chain(_code("signal", {"price": 182.5, "symbol": "NVDA"}),
                   {"id": "notify", "type": "TelegramNode",
                    "template": "{{ nodes.signal.symbol }} 매수 신호: {{ nodes.signal.price }}달러"})
    fixture = {"as_of": AS_OF, "nodes": {"notify": {"kind": "responder", "as_of": AS_OF}}}
    with patch.object(TelegramNode, "execute", side_effect=AssertionError("network send forbidden")):
        result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["notify"] == {"sent": True, "message_id": "replay-1"}
    assert result.outbox == [{"node_id": "notify", "text": "NVDA 매수 신호: 182.5달러",
                              "parse_mode": "HTML", "scope": None}]
    assert any(a["node_id"] == "notify" and a["kind"] == "responder" for a in result.assumptions)


@pytest.mark.asyncio
async def test_an_empty_telegram_template_reads_like_the_live_default():
    graph = _chain({"id": "notify", "type": "TelegramNode", "template": "   "})
    result = await replay(graph, {"as_of": AS_OF, "nodes": {"notify": {"kind": "responder", "as_of": AS_OF}}})
    assert result.passed, result.errors
    assert result.outbox[0]["text"] == "ProgramGarden notification"


def _ai_graph():
    schema = {"decision": {"type": "string", "enum": ["buy", "hold"]}, "reason": "string"}
    graph = _chain(
        _code("ind", {"rsi": 27.5}),
        {"id": "llm", "type": "LLMModelNode", "provider": "openai", "model": "gpt-4o"},
        {"id": "agent", "type": "AIAgentNode", "output_format": "structured", "output_schema": schema,
         "user_prompt": "RSI is {{ nodes.ind.rsi }}. buy or hold?"},
        {"id": "gate", "type": "IfNode", "left": "{{ nodes.agent.response.decision }}", "operator": "==",
         "right": "buy"},
        _code("buy", {"ordered": 1}))
    # llm feeds the agent through an ai_model edge, not the main chain.
    graph["edges"] = [e for e in graph["edges"] if not (e["from"] == "llm" or e["to"] == "llm")]
    graph["edges"] += [{"from": "ind", "to": "agent"}, {"from": "llm", "to": "agent", "type": "ai_model"},
                       {"from": "start", "to": "llm"}]
    next(e for e in graph["edges"] if e["from"] == "gate")["from_port"] = "true"
    return graph


def _ai_fixture(answer):
    return {"as_of": AS_OF, "nodes": {"llm": {"kind": "responder", "as_of": AS_OF},
                                       "agent": {"kind": "responder", "as_of": AS_OF, "answer": answer,
                                                 "label": "scenario"}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("answer,decision,buys", [
    ('{"decision": "buy", "reason": "oversold"}', "buy", True),
    ('```json\n{"decision": "hold", "reason": "wait"}\n```', "hold", False),
])
async def test_ai_answers_run_the_live_parser_and_both_branches(answer, decision, buys):
    result = await replay(_ai_graph(), _ai_fixture(answer))
    assert result.passed, result.errors
    assert result.outputs["agent"]["response"]["decision"] == decision
    assert ("buy" in result.executed) is buys
    prompt = next(a for a in result.assumptions if a["node_id"] == "agent")["prompt_preview"]
    assert prompt == "RSI is 27.5. buy or hold?"
    assert result.outputs["llm"]["connection"]["api_key"] is None


@pytest.mark.asyncio
async def test_a_malformed_ai_answer_never_takes_the_buy_branch():
    # The live parser keeps the raw text when JSON parsing fails; the decision
    # field is then absent, so the gate does not open.
    result = await replay(_ai_graph(), _ai_fixture("I think you should probably buy."))
    assert result.outputs["agent"]["response"] == "I think you should probably buy."
    assert "buy" not in result.executed


@pytest.mark.asyncio
async def test_ai_answers_per_split_item():
    from programgarden.replay_external import per_item_key
    graph = {"id": "ai-basket", "name": "AI basket", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "llm", "type": "LLMModelNode", "provider": "openai", "model": "gpt-4o"},
        {"id": "split", "type": "SplitNode", "array": [{"symbol": "AAPL", "exchange": "NASDAQ"},
                                                     {"symbol": "XOM", "exchange": "NYSE"}]},
        {"id": "agent", "type": "AIAgentNode", "output_format": "text",
         "user_prompt": "View on {{ nodes.split.item.symbol }}?"},
        {"id": "agg", "type": "AggregateNode", "mode": "collect"}],
        "edges": [{"from": "start", "to": "llm"}, {"from": "start", "to": "split"},
                  {"from": "split", "to": "agent"}, {"from": "llm", "to": "agent", "type": "ai_model"},
                  {"from": "agent", "to": "agg"}]}
    answers = {per_item_key("AIAgentNode", {"symbol": "AAPL", "exchange": "NASDAQ"}): "AAPL positive",
               per_item_key("AIAgentNode", {"symbol": "XOM", "exchange": "NYSE"}): "XOM negative"}
    fixture = {"as_of": AS_OF, "nodes": {"llm": {"kind": "responder", "as_of": AS_OF},
                                         "agent": {"kind": "responder", "as_of": AS_OF, "answers": answers}}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert sorted(result.outputs["agg"]["array"]) == ["AAPL positive", "XOM negative"]


FUTURES_CONNECTION = {"product": "overseas_futures", "provider": "ls-sec.co.kr", "paper_trading": True}


def _orderable_graph(price_expr="{{ nodes.quote.price }}"):
    graph = _chain(
        {"id": "broker", "type": "OverseasFuturesBrokerNode", "paper_trading": True},
        _code("quote", {"price": 6050.25}),
        {"id": "capacity", "type": "OverseasFuturesOrderableQuantityNode",
         "symbol": {"symbol": "MESZ26", "exchange": "CME"}, "side": "buy", "order_type": "limit",
         "price": price_expr},
        {"id": "size", "type": "CodeNode", "outputs": [{"name": "qty", "type": "number"}],
         "data": "{{ nodes.capacity.quantity }}",
         "code": "def execute(data, params, context):\n return {'qty': min(data, 2)}"})
    return graph


def _orderable_fixture(quantity):
    return {"as_of": AS_OF, "nodes": {
        "broker": recording("OverseasFuturesBrokerNode", {"paper_trading": True},
                            {"connection": FUTURES_CONNECTION},
                            {"type": "object", "required": ["connection"]}, as_of=AS_OF),
        "capacity": {"kind": "responder", "as_of": AS_OF, "orderable_quantity": quantity}}}


@pytest.mark.asyncio
async def test_orderable_quantity_answers_the_late_bound_request_through_the_live_parser():
    result = await replay(_orderable_graph(), _orderable_fixture(3))
    assert result.passed, result.errors
    assert result.outputs["capacity"] == {"quantity": 3, "verified": True, "error": None}
    assert result.outputs["size"]["qty"] == 2
    note = next(a for a in result.assumptions if a["node_id"] == "capacity")
    assert note["request"] == {"symbol": "MESZ26", "side": "2", "price": "6050.25"}
    assert note["orderable_quantity"] == 3


@pytest.mark.asyncio
async def test_orderable_quantity_still_refuses_an_invalid_request():
    result = await replay(_orderable_graph(price_expr=0.0), _orderable_fixture(3))
    assert not result.passed
    assert any("limit price" in e.get("message", "") for e in result.errors), result.errors


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [-1, 1.5, True, None])
async def test_orderable_quantity_answer_must_be_a_whole_number(bad):
    result = await replay(_orderable_graph(), _orderable_fixture(bad))
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_INVALID" for e in result.errors)


@pytest.mark.asyncio
async def test_a_responder_is_bound_to_the_shared_clock_and_known_types():
    graph = _chain({"id": "notify", "type": "TelegramNode", "template": "x"})
    result = await replay(graph, {"as_of": AS_OF, "nodes": {
        "notify": {"kind": "responder", "as_of": "2026-10-15T14:00:00Z"}}})
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in result.errors)
    graph = _chain({"id": "http", "type": "HTTPRequestNode", "method": "GET", "url": "https://x.invalid"})
    result = await replay(graph, {"as_of": AS_OF, "nodes": {"http": {"kind": "responder", "as_of": AS_OF}}})
    assert any(e["code"] == "REPLAY_CAPABILITY_BLOCKED" for e in result.errors)
