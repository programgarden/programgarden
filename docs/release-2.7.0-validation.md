# Version 2.7.0 release validation

Engine 2.7.0, core 2.7.0, finance 2.0.6 and community 2.3.2 are released
together on 2026-10-18. The base is main `55c4042f` (engine 2.6.7, core 2.6.3,
finance 2.0.5, community 2.3.1). The engine requires core ^2.7.0, finance
^2.0.6 and community ^2.3.2.

## Changes

- **Overseas stock minute bars (core 2.7.0, engine).**
  `OverseasStockHistoricalDataNode.interval` accepts `1m`, `5m`, `10m`, `15m`,
  `30m` and `60m`, read through LS g3203 (`ncnt` 1/5/10/15/30/60). Contract and
  limits: [stock history intervals](stock-history-interval-contract.md).
- **Futures fill-price recovery (engine, fix).** The fallback that fills a
  missing futures fill price read a client method, block and fields that do not
  exist. It now reads CIDBQ01800 per order date and matches `OvrsFutsOrdNo` by
  integer identity.
- **Replay recording kinds (engine, finance 2.0.6, community 2.3.2).** Per-item
  recordings inside SplitNode baskets, `ls_tape` (live LS read executors over
  recorded HTTP answers through the opt-in finance replay transport) and
  responders (Telegram outbox, LLMModel connection, AIAgent answers, futures
  orderable quantity). RollManagement and TimeBasedExit read the replay clock.
  Reference: [replay recording kinds](replay-recording-kinds.md).

## Live broker evidence for minute bars

One read-only g3203 call per `ncnt`, platform overseas-stock key, a stored
unexpired token (no token issuance; no running workflow used that key), NVDA
(`82NVDA`), `sdate=20261015`, `edate=20261016`, `qrycnt=40`, US market closed:

| ncnt | time (KST, 10-18) | HTTP | rsp_cd | rows | observed step |
| --- | --- | --- | --- | --- | --- |
| 15 | 01:34 | 200 | 00000 | 40 | 15 min |
| 1 | 01:52 | 200 | 00000 | 40 | 1 min |
| 5 | 01:52 | 200 | 00000 | 40 | 5 min |
| 10 | 01:52 | 200 | 00000 | 40 | 10 min |
| 30 | 01:52 | 200 | 00000 | 40 | 30 min (plus one session gap) |
| 60 | 01:52 | 200 | 00000 | 40 | 60 min |

Every answer had `tr_cont=Y`, ascending rows ending at the 18:00 local bar of
2026-10-16, and parsed with finance `G3203OutBlock`/`G3203OutBlock1`. 15-minute
bars started at 08:15 local time and 60-minute bars at 02:00, so extended-hours
bars are part of the answer. LS has no overseas-stock paper trading.

## What changes for running workflows

- New pods and app builds accept the six minute intervals for overseas stock
  history. Saved workflows that used them were refused by 2.6.1–2.6.7 static
  validation and become valid; nothing else about existing intervals changes.
- The futures fill-price fallback can now write a price into the local order
  ledger when a filled order had none (only when no managed futures
  reconciliation handler owns history).
- The finance replay transport is off unless a replay worker installs it; live
  request paths are unchanged.

## Verification

Local Python 3.12, two fresh virtual environments with the same third-party
packages as the 2.6.7 gate (pytest 8.4.2, pytest-asyncio 0.21.2, network not
used) and the four source packages installed in editable mode: one from this
tree (commits up to `981f8909`), one from `55c4042f`. Each package suite ran
from its own directory.

| Suite | 2.7.0 candidate | `55c4042f` (2.6.7) |
|---|---|---|
| Engine | 3590 passed, 29 skipped, 3 xfailed, 4 failed | 3529 passed, 29 skipped, 3 xfailed, 5 failed |
| Finance | 3451 passed, 10 failed | 3442 passed, 10 failed |
| Core | 1618 passed, 1 failed | 1618 passed, 1 failed |
| Community | 1612 passed, 9 failed | 1606 passed, 9 failed |

Every candidate failure also fails on the base: engine — three cancel-order
port assertions (`test_modify_order_empty_guard.py`) and
`test_replay_mapping_reports.py::test_report_computes_drawdown_from_actual_equity_series`;
finance — ten field-metadata example cases; core — the catalog metadata test
for `OverseasStockHistoricalDataNode` (it wanted a second example); community
— nine performance-report / portfolio-optimizer cases. The base's fifth engine
failure, `test_replay_fixture_binding.py::...[changed3]` (an `interval="1m"`
history request), passes now that `1m` is a supported interval.

After the gate, `693e2738` added a second (15-minute) catalog example to
`OverseasStockHistoricalDataNode`; the full core suite then passed (1619, no
failure: the pre-existing metadata failure is fixed) and the six engine files
that check node examples and catalogs passed (491).

New cases and their result on the base tree (failing first):

| File | Cases | On `55c4042f` |
|---|---|---|
| engine `test_replay_split_basket.py` | 9 | 6 fail (3 are compatibility checks that already held) |
| engine `test_replay_ls_tape.py` | 19 | the 17 cases of the first version all fail (no tape kind, no finance transport); the 2 added later need the same |
| engine `test_replay_responders.py` | 13 | all fail |
| engine `test_futures_fill_price_sync.py` | 4 | all fail |
| engine `test_stock_history_interval_contract.py` (rewritten) | 60 | 25 fail (minute intervals refused) |
| finance `test_replay_transport.py` | 9 | import error (module absent) |
| community `test_plugin_replay_clock.py` | 6 | 5 fail |

The tape tests block every socket and use synthetic answers generated from the
finance block models and a scenario ledger (placeholder account numbers, no
broker data). The fill-price tests use the LS paper capture of 2026-10-15
already in finance `tests/fixtures/tc_frames_paper_futures_20261015.json`.
The tape path was also run, outside the test suite, for the other read node
types (Korea/futures quotes, fundamentals, symbol queries, rankings, Korea and
futures history, futures contract info and orderable quantity): the live
executors ran without a network call; two synthetic answers lacked fields the
live readers require (a paper futures business date, a CIDBQ01400 `RecCnt`
echo), which the readers reported as errors, as they would for a real answer.

## Consumers

`VALIDATOR_VERSION` and `CONTRACT_VERSION` are unchanged. The runtime identity
changes, so skeleton catalogs keyed by it are re-seeded. `ReplayResult` has two
new fields (`outbox`, `assumptions`): a consumer that rebuilds `ReplayResult`
from every dataclass field of a worker answer needs the worker on 2.7.0 first or
at the same time. Pin all four packages exactly in every consumer.
