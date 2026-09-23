# Incremental replay foundation (not published)

This branch adds a server-owned BuildWorkspace, fresh node/cumulative execution,
strict replay contracts and an in-memory order-intent book. The public live
executor remains separate. A replay result does not authorize a broker order.

Native schema correction: the three REST MarketDataNode variants now advertise
only `values`, matching their actual live return envelope. The old singular
`value` was never emitted but remained in catalog declarations and could mislead
independent fixture design or generated bindings. AST output-contract checks now
compare actual quote rows with `values`. This does not add a runtime compatibility
alias or rewrite any customer workflow.

- `programgarden.incremental_build.BuildWorkspace`: admit one dependent node only
  after its upstream nodes are VERIFIED; verify references as well as edges.
  Repairs, edge changes, execution-plan changes and runtime changes invalidate
  evidence. JSON restoration preserves the same task identity. Concurrent/stale
  validation results cannot become current evidence. Validation cancellation and
  exhausted retry budgets stay BLOCKED. `attempts` counts every node and final
  validation, while `failure_streaks` counts consecutive unsuccessful results.
  Only a new PASS clears its streak. Six unsuccessful results block that target;
  the total384-attempt limit remains independent. Normal successful multi-turn
  modifications therefore do not exhaust a six-failure retry allowance.
- `programgarden.validation_replay.replay`: actual scheduler, expressions,
  CodeNode subprocess and condition/set operations; no forced deep-validation
  passes. External I/O requires exact fixtures, including per-symbol fixtures
  when iterating. Strict node input models and explicit output contracts reject
  coercion, missing fields and nonfinite values.
- `programgarden.replay_sources.source_contract_catalog`: native raw-source
  envelopes for private scenario preparation, including the actual SDK response
  schemas. This does not run transport or fabricate provider observations. The
  parser still executes and independently asserted outputs still determine PASS.
- `programgarden.replay_orders.SimulationBook`: fixture-only cash, positions,
  reserved orders, partial fills, cancellation and UNKNOWN reconciliation.
  Futures require explicit margin and multiplier; profit calculations are only
  the fixture model, not broker verification or performance evidence.
- `programgarden.replay_order_adapter.ReplayOrders`: shares the live new-order
  normalizer and modification-target resolver; never invokes a broker transport.
  All three products have new/modify/cancel graph adapters. A change response
  acknowledges a request, not its completion. Only subsequent matching fixture
  evidence at a broker-observation node applies cancellation/replacement. Open-order
  snapshots cannot hide remaining orders or disagree with their quantities/market.
  Partial-fill replacement quantity semantics and special auction types remain
  unsupported rather than guessed. Partial fills followed by cancellation are
  supported, including fills racing with cancellation acknowledgements.
- `programgarden.replay_sqlite.execute_sqlite`: uses real SQLite reservation
  writes/reads in fresh disposable storage. Standalone node validation executes
  ancestor setup in the same workspace; cumulative validation starts fresh.
  SQL cannot attach outside databases, load extensions or change pragmas.
- `programgarden.replay_scenarios`: exact expected rejection/UNKNOWN assertions
  produce a separate scenario assessment. Raw execution failures remain visible;
  contract or mapping defects cannot be accepted as an expected rejection.
- `programgarden_core.expression.evaluator.DateNamespace(as_of=...)`: optional
  fixed timezone-aware replay clock. Live default behavior is unchanged. Replay
  expressions and CodeNode helpers use the same instant when a fixture supplies
  it. Direct imports of nondeterministic clocks still require explicit handling.

The package modules must run inside the dedicated credential-free Linux worker.
Calling `replay()` in an arbitrary host process is not an OS isolation guarantee.
The worker enforces network denial, removes inherited credentials/descriptors,
limits resources, and terminates the process group on timeout or cancellation.
Unsupported nodes, absent fixtures and unsupported contracts block verification.

## Clock and fixture replacement

SessionGateNode replay evaluates the real node's pure session decision at the
fixture's explicit timezone-aware instant. Missing clocks block validation;
regular-session boundaries, weekends, daylight saving time and explicit closures
remain observable in actual downstream branches. No wall-clock or forced-allow
result is used.

Trusted fixture replacement invalidates node evidence without resetting the graph
or retry ledger. An identical suite is an idempotent resume; an empty replacement
is BLOCKED. Malformed, oversized or nonfinite fixture collections are rejected
before replacing the stored suite. Focused session/workspace tests: 27 passed.

## Evidence and remaining release gates

External replay requires per-symbol recordings with explicit contracts. Missing
market identity or a mismatched symbol is rejected rather than borrowing another
symbol's result. Domestic symbol-only inputs use KRX identity. These fixtures
are scenario assumptions, not observed broker availability. The removed FMP
provider has no replay adapter.

Each validation records task/plan/workflow identity, graph/node/fixture hashes,
engine/source versions, run IDs, mode and results. Source identity covers all
engine/core/community/finance Python files and calculation dependency versions;
an editable plugin change or numpy/pandas change cannot reuse old proof.
The host persists leased
claims and checks returned identities. Final replay reloads the saved graph and
requires independent expected-output assertions; it is separate from publication.
Order graphs additionally require `expected_simulation` contracts over cash,
reserved cash, positions, orders and zero live submissions. The receiving host
rechecks these assertions; a correct-looking node result with a wrong account
state cannot become READY. Failed chains retain earlier intents and book state.

This is an unreleased foundation. Trusted strategy-specific fixtures, complete
contract coverage, remaining broker-specific lifecycle semantics, public
entry-path gates, queue semantics and AI tool integration remain in progress.
No new package version has been published and no incremental gate is enabled in
production. Do not describe a passing fixture as "error-free live trading".

## Request-bound replay (September 23, unreleased)

`replay_external.request_identity` normalizes native schema defaults and retains
every executable request field. Recordings bind the resolved request, iteration
item and shared timezone-aware clock. Changing a URL, HTTP method/body, symbol,
date range, interval or paper mode cannot reuse a recording under the same node
ID. Unknown request fields fail explicitly. The trusted `recording` constructor
checks an output contract but does not establish fixture provenance; callers
must provide independently reviewed inputs/expectations.

Each `REPLAY_FIXTURE_MISMATCH` — resolved request, shared replay clock or actual
iteration item — now carries a deterministic, secret-free field-level diff so the
host can tell the model exactly what differed. The `ContractViolation.detail`
(surfaced verbatim in the diagnostic dict, not truncated into the message) is
`{"recorded": {...}, "resolved": {...}, "differing": ["connection.provider", ...]}`:
top-level keys present on only one side, and for object fields (`symbol`,
`connection`, `config`) the differing nested keys as `key.subkey`. The message
also names the differing paths (bounded). Both operands are already-normalized
request identities, iteration items or the two clocks; `request_identity` admits
only non-secret provider/product/paper mode/broker node id/credential reference,
and the recorded request is already public to the model through build guidance,
so the diff is precise diagnostics rather than an oracle leak — no credential
secret can enter it. The comparison uses the same canonical JSON identity as the
recording hash, so it reports a difference on exactly the paths that made the
hashes disagree. The receiving host and AI layer must forward `detail` alongside
`code`/`message`. This is a local, unreleased library change; no package version
was bumped and no publication accompanies it.

Validator identity is now `incremental-replay-2`. Runtime identity also includes
`croniter` and `pytz` versions, preventing time-library changes from reusing proof.

Schedule replay executes the actual startup executor, cancelling and draining
its timer before any scheduled event runs. The immediate initial trigger is
preserved even away from a cron tick. This verifies a single startup traversal,
not recurring event delivery. Missing clocks and invalid timezones/safety limits
block validation.

TradingHoursFilter replay shares the live predicate with an explicit aware
instant. Live's inclusive minute boundary is retained; an out-of-window fixture
reports `REPLAY_TIME_WAIT_BLOCKED`, because the actual node waits rather than
taking an immediate blocked branch. Temporal wait/resume replay is not supported.
Malformed times/days now raise instead of failing open; overnight windows require
SessionGateNode. The live default remains wall-clock based.

Telegram uses request-bound external response fixtures without invoking its
network implementation. A fixture's `sent=true` is simulated evidence, never
delivery verification or authorization. Credential linkage and actual delivery
remain separate checks.

## Existing deep-validation projection correction

The public executor's simulated array narrowing now selects the matching entry
from the node's configured input. It must not replace that entry with a raw
upstream quote, which can introduce numeric fields into a symbol-only contract
or override a configured order quantity. Live execution behavior is unchanged.
The regression exercises quote-to-LS-fundamentals data flow without broker calls.
Provider fixtures do not establish live data availability. The removed FMP node
is rejected at admission; its provider-specific replay adapter is also removed.

## Native parser and computation coverage (September 23, unreleased)

FieldMapping, the six display envelopes and PerformanceReport execute their native
implementations. PerformanceReport requires the actual quantstats extra in the
locked worker and coordinator; a missing extra fails validation. A rendered
display envelope does not assert browser rendering. The report regression checks
the actual -18.18% drawdown of a fixed equity series, including in the private
worker integration suite.

`replay_sources` separates raw source records from asserted node outputs. FileReader
parses recorded bytes through its native parser without reading host files. FearGreed
normalization, index constituent exchange selection, futures expiry/month selection,
Yahoo screener predicates and CIDBQ01400 echo/capacity checks use native code. The
record binds the request, item and clock. Missing source data blocks; it is never
replaced with a generated successful node result. LS-backed screener enrichment
uses raw g3101 SDK blocks and the same native filter logic. Provider availability,
user file presence and real account capacity are not certified by simulation.

Throttle uses the fixture clock and real cooldown/pending state, including
pass_first=false. A regression exposed a live scheduler defect: initial and Split
traversals ignored its waiting result. Those traversals now block dependent nodes
and joins while preserving independent branches. The event traversal now applies
the same guards rather than stopping unrelated branches. Legacy dry-run
pass-through remains outside replay.

Every registered node type now has an explicit dispatch boundary. This inventory
does not mean every configuration, temporal event sequence or broker lifecycle is
supported. Unsupported semantics remain blocking. The combined engine regression
suite passes 310 checks; no conversational accuracy percentage follows from it.

### LS quote and account identity correction (unreleased)

The Screener transport now builds the complete SDK g3101 request (`delaygb`,
`keysymbol`, `exchcd`, `symbol`) using the existing exchange mapping. It rejects
unknown exchanges, wrong response identities, missing credentials/data and
unsupported filters instead of dropping conditions. A successful query with no
matching symbols returns an empty list. Raw/master mixed input enriches missing
observations individually. Repeated quote reads within one invocation are avoided.

Replay request identity retains the selected non-secret broker connection,
including credential reference, product, paper mode and broker node ID. Changing
that identity cannot reuse a recorded account/market observation. No secret values
are accepted in connection recordings. These are local changes, not a package or
production release. The targeted engine sweep passes312 tests; the smaller
LS/request-binding sweep passes97 (overlapping cases, not accuracy percentages).

### Recurring events and retained state (unreleased)

Validator3 accepts at most32 recorded events per scenario. They enter the native
event loop after the actual initial traversal. SQLite, cooldowns, positions,
reservations and order history remain in the same disposable job. Each new replay
still starts with fresh storage. Recorded schedule ticks must match the configured
cron/timezone/count; this checks delivery consequences, not wall-clock delivery.
Realtime records bind source identity, request and time. The native scheduler
chooses downstream nodes; recordings cannot specify a bypass target or replace
cash/positions. Quotes advance independently and old quotes can fail freshness.

Final checks require independent assertions and path coverage for every recorded
event, including intermediate results. Order graphs additionally require financial
state assertions at each event. The host repeats these checks on the worker result.
Existing value assertions also run during node/chain validation as soon as their
node is reached; a schema-valid incorrect number cannot become VERIFIED merely
because finalization has not happened yet. Unreached paths still require explicit
positive coverage rather than a manufactured execution result.
Provider availability, websocket subscription and TradingHours wait/resume remain
outside this recorded-event contract. There is no implied live authorization.

### Native time-gate traversal correction (unreleased)

Startup, per-item Split and realtime traversals now honor disabled Schedule
triggers and TradingHours decisions. Default/`passed` edges cannot run on timeout;
explicit `blocked` edges cannot run after an in-window pass. A selected branch
can still reach a common merge, while an unrelated parent does not bypass a
refused required gate. The core node returns its declared `blocked` boolean.
Twelve native regression cases failed against the original executor/core and
passed with the correction. The broader focused suite passed90 checks, with six
additional merge-order cases included. Tests have no broker/network/message
nodes. Positive-duration waiting in replay is still BLOCKED, not simulated by
forcing a pass. No package publication or rollout is implied.

Native recurring traversal previously ignored If branch results and pre-executed
Split before its upstream guard. It also retained input ports from a prior event.
The corrected traversal applies guards before branches, clears stale inputs and
outputs, and preserves independent branches after a failed/throttled source.
Rate-limit evaluation uses the same native policy with an explicit replay clock.

The stock order adapter no longer invents implicit idempotency by hashing only
node/intent. Repeated submissions are visible and can fail the independent risk
scenario. Futures use the native cycle/invocation identity. Replay does not claim
coverage of a deployment's optional durable stock-idempotency registry; that
execution-profile binding remains a separate release requirement.


### Graph removals and shared settings (unreleased)

`BuildWorkspace.remove_node` removes one node and its incident edges. All remaining
nodes become STALE because roots, iteration and implicit connections may change.
Removed-node attempts remain recorded; remove/re-add is not a retry reset. Missing
required output/path assertions still fail final replay after a node is removed.

`update_header` accepts only name, description, version, inputs, resource limits,
notes and tags. It checks the native JSON schema and rejects unknown setting fields.
Identity, graph nodes/edges, credentials and evidence are not header edits. Any
changed header invalidates existing proof; an identical revision-checked retry is
a no-op. The host independently enforces ownership and a repair's layout policy.
Thirty focused workspace/replay tests pass. These are unreleased library changes,
not evidence of public deployment or live trading.

## Requirements-first contract preparation

`replay_contracts.validate_contract` checks an assertion schema without inventing
an output value or running candidate code. A coordinator may compile independent
test specifications before construction; this is not a validation PASS. Native
node and cumulative-chain execution, final expectations and saved-byte readback
remain required. Unknown schema keywords fail closed.

Domestic REST account discovery now includes the fields actually emitted by the
finance evidence parser plus executor aliases. Runtime tests compare the composed
output with the catalog both with and without monetary evidence. Missing costs or
P&L remain null with an explicit unavailable status, rather than becoming zero.

## CodeNode output guidance correction (unreleased, September23)

The native schema/examples now distinguish the entire undeclared `result` value
from declared output-key mapping. With no outputs, `return 3` exposes result=3,
while `return {"result":3}` exposes result={"result":3}. Declaring the result port
maps the returned dictionary's result key to that port. A single declared port
also accepts a scalar. Deep/replay rejects missing/wrong declared outputs; the
existing live fallback is documented separately and is not verification evidence.
The generic code editor example returns data directly to avoid accidental nesting.
English and Korean output help follow the same contract. No executor behavior or
package version changed.65 CodeNode execution/replay contract checks passed in a
network-disabled Linux container. Source fingerprint changes invalidate old proof;
revalidate before any new publication. No PyPI publication accompanies this edit.
