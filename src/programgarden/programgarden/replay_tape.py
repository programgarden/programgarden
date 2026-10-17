"""Replay LS REST read nodes through their real executors over recorded HTTP answers.

A recording ``{"kind": "ls_tape", "as_of": ..., "tape": [entry, ...]}`` lets the
validation worker run the node's own executor and the finance TR parser over
scenario answers. Each entry is one recorded HTTP answer::

    {"tr": "COSOQ00201",                          # LS tr_cd
     "request": {"COSOQ00201InBlock1": {...}},    # the JSON body the node sends
     "ignore": ["COSOQ00201InBlock1.BaseDt"],     # optional: paths not compared
     "tr_cont": "N", "tr_cont_key": "",           # optional continuation header
     "status": 200,                               # optional, default 200
     "headers": {"tr_cont": "N"},                 # optional response headers
     "json": {"rsp_cd": "00000", ...}}            # the response body

A request is answered by the first entry with the same ``tr``, continuation
header and body (exactly, apart from the listed ``ignore`` paths, which exist
for request fields the executor fills from the wall clock, such as a query
date). A request no entry answers fails the node with
``REPLAY_FIXTURE_REQUIRED`` naming the TR. Order TRs, token issuance and token
reissue are refused (``REPLAY_CAPABILITY_BLOCKED``). The node never sees a
credential: it reads a non-secret placeholder, and its LS client is a fresh
replay client with no login (``programgarden_finance.ls.replay_transport``).

Tape answers are scenario assumptions written by the suite author, never broker
evidence. Realtime (websocket) nodes and order nodes are not tape nodes.
"""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Dict, List, Optional

from programgarden.replay_contracts import ContractViolation

TAPE_NODES = frozenset({
    f"{product}{kind}Node"
    for product in ("OverseasStock", "OverseasFutures", "KoreaStock")
    for kind in ("Account", "MarketData", "HistoricalData", "Fundamental", "SymbolQuery", "OpenOrders")
    if not (product == "OverseasFutures" and kind == "Fundamental")
}) | {"KoreaStockRankingNode", "OverseasStockRankingNode", "FuturesContractNode",
      "OverseasFuturesContractInfoNode", "OverseasFuturesOrderableQuantityNode"}

_DEFAULT_HEADERS = {"Content-Type": "application/json; charset=utf-8", "tr_cont": "N", "tr_cont_key": ""}
_MAX_REPORTED = 8


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _without(body: Any, paths: List[str]) -> Any:
    """``body`` with the dotted ``paths`` removed (a copy)."""
    result = deepcopy(body)
    for path in paths:
        parts = path.split(".")
        node = result
        for part in parts[:-1]:
            node = node.get(part) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(parts[-1], None)
    return result


class LsTape:
    """The installed replay transport of one tape node execution."""

    def __init__(self, node_id: str, record: Dict[str, Any], paper_trading: bool):
        entries = record.get("tape")
        if not isinstance(entries, list) or not entries:
            raise ContractViolation(node_id, "An ls_tape recording needs a non-empty tape list",
                                    "REPLAY_FIXTURE_INVALID")
        self.node_id = node_id
        self.paper_trading = bool(paper_trading)
        self.entries: List[Dict[str, Any]] = []
        for index, entry in enumerate(entries):
            where = f"{node_id}.tape[{index}]"
            if not isinstance(entry, dict) or not isinstance(entry.get("tr"), str) or not entry["tr"]:
                raise ContractViolation(where, "A tape entry needs its tr code", "REPLAY_FIXTURE_INVALID")
            if not isinstance(entry.get("request"), dict) or not isinstance(entry.get("json"), dict):
                raise ContractViolation(where, "A tape entry needs a request body and a json answer",
                                        "REPLAY_FIXTURE_INVALID")
            ignore = entry.get("ignore", [])
            if not isinstance(ignore, list) or not all(isinstance(p, str) and p for p in ignore):
                raise ContractViolation(where, "ignore must list dotted request paths", "REPLAY_FIXTURE_INVALID")
            status = entry.get("status", 200)
            if isinstance(status, bool) or not isinstance(status, int):
                raise ContractViolation(where, "status must be an integer", "REPLAY_FIXTURE_INVALID")
            _canon(entry["request"]), _canon(entry["json"])  # finite JSON only
            self.entries.append(entry)
        self.calls: List[Dict[str, Any]] = []
        self.misses: List[Dict[str, Any]] = []
        self.refusals: List[Dict[str, Any]] = []

    # -- transport protocol (programgarden_finance.ls.replay_transport) ---------
    def answer(self, tr_cd: str, url: str, header: Dict[str, Any], body: Dict[str, Any]):
        from programgarden_finance.ls.replay_transport import ReplayTransportRefused

        if url.rstrip("/").endswith("/order"):
            self.refusals.append({"kind": "order", "tr": tr_cd})
            raise ReplayTransportRefused(f"order TR {tr_cd} is not answered by a tape")
        cont = (str(header.get("tr_cont") or "N"), str(header.get("tr_cont_key") or ""))
        nearest: Optional[Dict[str, Any]] = None
        for index, entry in enumerate(self.entries):
            if entry["tr"] != tr_cd:
                continue
            if (str(entry.get("tr_cont", "N")), str(entry.get("tr_cont_key", ""))) != cont:
                continue
            ignore = entry.get("ignore", [])
            if _canon(_without(body, ignore)) == _canon(_without(entry["request"], ignore)):
                self.calls.append({"tr": tr_cd, "entry": index})
                headers = {**_DEFAULT_HEADERS, "tr_cd": tr_cd, **(entry.get("headers") or {})}
                return entry.get("status", 200), deepcopy(entry["json"]), headers
            if nearest is None:
                nearest = entry
        from programgarden.replay_external import mismatch_detail
        miss: Dict[str, Any] = {"tr": tr_cd, "tr_cont": cont[0]}
        if nearest is not None:
            miss.update(mismatch_detail(_without(nearest["request"], nearest.get("ignore", [])),
                                        _without(body, nearest.get("ignore", []))))
        self.misses.append(miss)
        raise ReplayTransportRefused(f"no tape answer for TR {tr_cd}")

    def refused(self, kind: str, detail: str) -> None:
        self.refusals.append({"kind": kind, "detail": str(detail)[:200]})


class _TapeContext:
    """The replay context as a live read node sees it under a tape.

    Live read paths run (no dry-run or deep-validation shortcut) and the node
    reads a non-secret placeholder credential instead of the context secrets.
    """

    is_dry_run = False
    is_deep_validate = False

    def __init__(self, context, tape: LsTape):
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_tape", tape)

    def __getattr__(self, name):
        return getattr(self._context, name)

    def __setattr__(self, name, value):
        setattr(self._context, name, value)

    def get_credential(self, credential_id: str = "credential_id"):
        return {"appkey": "REPLAY", "appsecret": "REPLAY", "paper_trading": self._tape.paper_trading}


def _paper_trading(config: Dict[str, Any]) -> bool:
    connection = config.get("connection")
    return bool(connection.get("paper_trading")) if isinstance(connection, dict) else False


async def execute_tape(runner, node_id: str, node_type: str, config: Dict[str, Any], context,
                       record: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Run the node's live executor with its LS REST TRs answered from ``record``."""
    from programgarden.executor import WorkflowExecutor
    from programgarden_finance.ls.replay_transport import use_replay_transport

    if not context.validation_as_of or record.get("as_of") != context.validation_as_of:
        raise ContractViolation(node_id, "Recording does not match the shared replay clock; differs at as_of",
                                "REPLAY_FIXTURE_MISMATCH", {"recorded": {"as_of": record.get("as_of")},
                                "resolved": {"as_of": context.validation_as_of}, "differing": ["as_of"]})
    tape = LsTape(node_id, record, _paper_trading(config))
    with use_replay_transport(tape):
        output = await WorkflowExecutor.execute_node(runner, node_id, node_type, config,
                                                     _TapeContext(context, tape), **kwargs)
    if tape.refusals:
        raise ContractViolation(node_id, "The node asked for a call a tape never makes: "
                                + ", ".join(sorted({r["kind"] for r in tape.refusals})),
                                "REPLAY_CAPABILITY_BLOCKED", {"refused": tape.refusals[:_MAX_REPORTED]})
    if tape.misses:
        trs = ", ".join(sorted({m["tr"] for m in tape.misses}))
        first = tape.misses[0]
        suffix = f"; differs at {', '.join(first['differing'][:6])}" if first.get("differing") else ""
        raise ContractViolation(node_id, f"No ls_tape answer for TR {trs}{suffix}", "REPLAY_FIXTURE_REQUIRED",
                                {"misses": tape.misses[:_MAX_REPORTED]})
    runner.outcome.assumptions.append({"node_id": node_id, "kind": "ls_tape",
                                       "trs": [call["tr"] for call in tape.calls][:32]})
    return output
