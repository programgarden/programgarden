"""Request-independent responders: answers built for the request the node actually makes.

Some external nodes bind values that exist only at run time (a price a CodeNode
computes, an order result, an AI prompt built from indicators), so no recording
made before execution can match their request. A responder recording answers
whatever request the node resolves, through the node's real parser, and is
labelled a scenario assumption (``ReplayResult.assumptions``), never broker or
provider evidence::

    {"kind": "responder", "as_of": "<fixture clock>", ...}

- ``TelegramNode``: renders the message exactly as the live node would, never
  sends it, returns ``{"sent": True, "message_id": "replay-N"}`` and appends
  ``{node_id, text, parse_mode}`` to ``ReplayResult.outbox``.
- ``LLMModelNode``: the live executor's non-secret ``connection`` output
  (no credential is read; ``api_key`` stays ``None``).
- ``AIAgentNode``: ``answer`` (or ``answers`` keyed by
  ``replay_external.per_item_key`` of the iterated/split item) is the raw text a
  model would write; the live parser (``output_format``/``output_schema``,
  presets applied) produces ``response``. No model is called.
- ``OverseasFuturesOrderableQuantityNode``: ``orderable_quantity`` (an integer
  >= 0) is the scenario's stated capacity. A CIDBQ01400 response echoing the
  ACTUAL resolved request is built and read by the live parser.
"""
from __future__ import annotations

from decimal import Decimal
import json
from typing import Any, Dict

from programgarden.replay_contracts import ContractViolation

RESPONDER_NODES = frozenset({"TelegramNode", "LLMModelNode", "AIAgentNode",
                             "OverseasFuturesOrderableQuantityNode"})
_PROMPT_PREVIEW = 2000


def _check_clock(node_id: str, record: Dict[str, Any], context) -> None:
    if not context.validation_as_of or record.get("as_of") != context.validation_as_of:
        raise ContractViolation(node_id, "Recording does not match the shared replay clock; differs at as_of",
                                "REPLAY_FIXTURE_MISMATCH", {"recorded": {"as_of": record.get("as_of")},
                                "resolved": {"as_of": context.validation_as_of}, "differing": ["as_of"]})


def _current_item(node_type: str, config: Dict[str, Any], context):
    """(found, item) of the iteration or split branch this execution runs for."""
    from programgarden.replay_external import branch_item
    if context._iteration_total:
        return True, context._iteration_item
    branch = branch_item(context, config)
    return (True, branch[2]) if branch is not None else (False, None)


def _telegram(runner, node_id, config, context, record):
    template = config.get("template") or ""
    # Same text rule as TelegramNode.execute (no render_template on the engine context).
    text = template if isinstance(template, str) and template.strip() else "ProgramGarden notification"
    outbox = runner.outcome.outbox
    outbox.append({"node_id": node_id, "text": text, "parse_mode": "HTML",
                   "scope": config.get("_branch_scope")})
    return {"sent": True, "message_id": f"replay-{len(outbox)}"}


def _llm_model(runner, node_id, config, context, record):
    return {"connection": {
        "provider": config.get("provider", "openai"), "model": config.get("model", "gpt-4o"),
        "api_key": None, "_llm_node_id": node_id, "base_url": config.get("base_url"),
        "organization": config.get("organization"), "api_version": config.get("api_version"),
        "temperature": config.get("temperature", 0.7), "max_tokens": config.get("max_tokens", 1000),
        "seed": config.get("seed"), "streaming": config.get("streaming", False)}}


def _ai_agent(runner, node_id, config, context, record):
    from programgarden.executor import AIAgentNodeExecutor
    from programgarden.replay_external import per_item_key

    if "answers" in record:
        found, item = _current_item("AIAgentNode", config, context)
        answers = record["answers"]
        key = per_item_key("AIAgentNode", item) if found else None
        if not isinstance(answers, dict) or key not in answers:
            raise ContractViolation(node_id, f"No responder answer for item {key}", "REPLAY_FIXTURE_REQUIRED")
        raw = answers[key]
    elif "answer" in record:
        raw = record["answer"]
    else:
        raise ContractViolation(node_id, "An AI responder needs answer or answers", "REPLAY_FIXTURE_INVALID")
    if not isinstance(raw, str):
        raise ContractViolation(node_id, "A responder answer is the raw text a model writes",
                                "REPLAY_FIXTURE_INVALID")
    preset = config.get("preset")
    if preset and preset != "custom":
        from programgarden_core.presets import PresetLoader
        config = PresetLoader.apply_preset(preset, config)
    parsed = AIAgentNodeExecutor()._parse_output(
        raw, config.get("output_format", "text"), config.get("output_schema"), context, node_id)
    prompt = config.get("user_prompt", "")
    if not isinstance(prompt, str):
        prompt = json.dumps(prompt, ensure_ascii=False, default=str)
    runner.outcome.assumptions.append({"node_id": node_id, "kind": "responder", "node_type": "AIAgentNode",
                                       "prompt_preview": prompt[:_PROMPT_PREVIEW],
                                       "label": record.get("label")})
    return {"response": parsed}


def _orderable_quantity(runner, node_id, config, context, record):
    from programgarden.futures_orderable import (
        FuturesCapacityEvidenceError, build_orderable_request, read_orderable_quantity)
    from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01400.blocks import CIDBQ01400Response

    quantity = record.get("orderable_quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise ContractViolation(node_id, "orderable_quantity must be an integer >= 0", "REPLAY_FIXTURE_INVALID")
    try:
        request = build_orderable_request(config)
    except FuturesCapacityEvidenceError as exc:
        raise ContractViolation(node_id, str(exc), "REPLAY_CONTRACT_FAILED") from exc
    echo = request.model_dump()
    echo["OvrsDrvtOrdPrc"] = str(Decimal(str(echo["OvrsDrvtOrdPrc"])))  # LS echoes price as text
    response = CIDBQ01400Response.model_validate({
        "header": None, "block1": {**echo, "AcntNo": ""}, "block2": {"RecCnt": 1, "OrdAbleQty": quantity},
        "status_code": 200, "rsp_cd": "00000", "rsp_msg": "scenario answer", "error_msg": None})
    try:
        value = read_orderable_quantity(response, request)
    except FuturesCapacityEvidenceError as exc:  # pragma: no cover - built to match
        raise ContractViolation(node_id, str(exc), "REPLAY_CONTRACT_FAILED") from exc
    runner.outcome.assumptions.append({"node_id": node_id, "kind": "responder",
                                       "node_type": "OverseasFuturesOrderableQuantityNode",
                                       "request": {"symbol": echo["IsuCodeVal"], "side": echo["BnsTpCode"],
                                                   "price": echo["OvrsDrvtOrdPrc"]},
                                       "orderable_quantity": quantity, "label": record.get("label")})
    return {"quantity": value, "verified": True, "error": None}


_RESPONDERS = {"TelegramNode": _telegram, "LLMModelNode": _llm_model, "AIAgentNode": _ai_agent,
               "OverseasFuturesOrderableQuantityNode": _orderable_quantity}


def respond(runner, node_id: str, node_type: str, config: Dict[str, Any], context,
            record: Dict[str, Any]) -> Dict[str, Any]:
    _check_clock(node_id, record, context)
    handler = _RESPONDERS.get(node_type)
    if handler is None:
        raise ContractViolation(node_id, "No responder for this node type", "REPLAY_CAPABILITY_BLOCKED")
    if node_type == "TelegramNode":
        runner.outcome.assumptions.append({"node_id": node_id, "kind": "responder", "node_type": node_type,
                                           "note": "message collected in outbox, not sent"})
    return handler(runner, node_id, config, context, record)
