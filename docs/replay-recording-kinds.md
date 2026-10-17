# Replay recording kinds (engine 2.7.0)

`validation_replay.replay(definition, fixture)` runs a workflow without
credentials or network. Computation nodes run for real; every external node
needs a recording in `fixture["nodes"][node_id]`. All recordings are bound to the
shared fixture clock (`as_of`). This page lists the recording kinds; the
existing node-output recording is unchanged.

| Kind | Shape | Node runs | Typical use |
| --- | --- | --- | --- |
| node output (default) | `{request, as_of, item, output, contract}` | no (output replayed) | any FIXTURE node |
| per-item group | `{items: {key: record}}` | as the record says | auto-iteration, SplitNode baskets |
| raw source | `{kind: "raw_source", request, as_of, item, source, source_contract}` | native parser | MarketUniverse, FuturesContract, ContractInfo, OrderableQty, Screener |
| `ls_tape` | `{kind: "ls_tape", as_of, tape: [...]}` | live executor + finance parser | LS REST read nodes |
| `responder` | `{kind: "responder", as_of, ...}` | live parser on a scenario answer | Telegram, LLMModel, AIAgent, futures OrderableQty |

Answers from tapes and responders are scenario assumptions written by the suite
author. `ReplayResult.assumptions` names every node they answered; they are never
broker or provider evidence.

## Per-item groups inside SplitNode branches

A node inside a split branch runs once per item with `_branch_scope =
"<split_id>#<index>"`. A group recording `{"items": {key: record}}` is selected
by the item at that index of the split's `items` output. Keys come from
`replay_external.per_item_key(node_type, item)`:

- a symbol item: `EXCHANGE:SYMBOL` (a domestic node's item without an exchange:
  `KRX:SYMBOL`);
- any other item (a row without an exchange, a number, a text): its content hash.

Each selected record must name that item (`record["item"]`). A missing key is
`REPLAY_FIXTURE_REQUIRED` (the message names the key and the branch); a record
made for another item is `REPLAY_FIXTURE_MISMATCH`. Parallel branches are safe:
the item comes from the array, not from the split's single `item` slot. A flat
record keeps its meaning: one request identity for every item, `item` null.

## `ls_tape`

```json
{"kind": "ls_tape", "as_of": "2026-10-16T14:00:00Z", "tape": [
  {"tr": "COSOQ00201",
   "request": {"COSOQ00201InBlock1": {"RecCnt": 1, "BaseDt": "20261016", "CrcyCode": "ALL", "AstkBalTpCode": "00"}},
   "ignore": ["COSOQ00201InBlock1.BaseDt"],
   "status": 200,
   "headers": {"tr_cont": "N", "tr_cont_key": ""},
   "json": {"rsp_cd": "00000", "rsp_msg": "...", "COSOQ00201OutBlock1": {}, "...": []}}]}
```

The node's live executor runs under the finance replay transport
(`programgarden_finance.ls.replay_transport`):

- every REST TR is answered by the first entry with the same `tr`, continuation
  header (`tr_cont`, `tr_cont_key`; default `N` and empty) and JSON body. The
  body is compared exactly, except the dotted `ignore` paths, which exist for
  request fields the executor fills from the wall clock (query dates);
- the node reads a non-secret placeholder credential and gets a fresh replay LS
  client (placeholder token, no login, never cached in `LSClientManager`);
- an unanswered request fails the node with `REPLAY_FIXTURE_REQUIRED`, naming
  the TR and the body paths that differ from the nearest entry of that TR;
- order TRs, token issuance and token reissue are refused:
  `REPLAY_CAPABILITY_BLOCKED`. A recorded token failure is not retried;
- websocket (`Real*`) nodes and order nodes are not tape nodes.

The transport is a `ContextVar`: other tasks in the same event loop never see
it. Build the `request` with the finance request models (`model_dump()` of the
InBlock the executor sends) rather than by hand. Live read code keeps its own
wall-clock reads (for example `observed_at`, query dates, contract selection
by today's date); use `ignore` or the raw-source recording where the fixture
clock matters.

## `responder`

- **TelegramNode** `{kind, as_of}`: the message text is the resolved `template`
  (or `ProgramGarden notification` when it is blank), never sent. Output
  `{"sent": true, "message_id": "replay-N"}`; the text is appended to
  `ReplayResult.outbox` as `{node_id, text, parse_mode, scope}`.
- **LLMModelNode** `{kind, as_of}`: the live executor's non-secret
  `connection` (no credential is read, `api_key` is null).
- **AIAgentNode** `{kind, as_of, answer}` or `{kind, as_of, answers: {key: text}}`
  (keys from `per_item_key` of the iterated/split item): the raw text a model
  would write, parsed by the live output parser with presets, `output_format` and
  `output_schema`. A text that is not JSON stays text (as live), so a field
  binding such as `response.decision` is absent. The resolved prompt is shown in
  `assumptions[].prompt_preview` (at most 2000 characters).
- **OverseasFuturesOrderableQuantityNode** `{kind, as_of, orderable_quantity}`:
  a CIDBQ01400 answer for the request the node actually resolved (including a
  price bound to a CodeNode output), echoing it and carrying the scenario's
  quantity, read by the live parser. An invalid request (no contract, no limit
  price) still fails.

## Fixture clock in community plugins

RollManagement and TimeBasedExit (community 2.3.2) read `context.validation_as_of`
when present, so expiry distance and holding days are judged at the fixture
instant. Live contexts keep the wall clock.

## Not covered

Account/open-order answers recomputed from the simulated book after fills,
exchange calendars beyond those already supported, realtime bursts and order-TR
fakes are not part of 2.7.0.
