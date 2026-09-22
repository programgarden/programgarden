# Incremental replay foundation (not published)

This branch adds a server-owned BuildWorkspace, fresh node/cumulative execution,
strict replay contracts and an in-memory order-intent book. The public live
executor remains separate. A replay result does not authorize a broker order.

- `programgarden.incremental_build.BuildWorkspace`: admit one dependent node only
  after its upstream nodes are VERIFIED; verify references as well as edges.
  Repairs, edge changes, execution-plan changes and runtime changes invalidate
  evidence. JSON restoration preserves the same task identity. Concurrent/stale
  validation results cannot become current evidence. Validation cancellation and
  exhausted attempts stay BLOCKED.
- `programgarden.validation_replay.replay`: actual scheduler, expressions,
  CodeNode subprocess and condition/set operations; no forced deep-validation
  passes. External I/O requires exact fixtures, including per-symbol fixtures
  when iterating. Strict node input models and explicit output contracts reject
  coercion, missing fields and nonfinite values.
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

## Existing deep-validation projection correction

The public executor's simulated array narrowing now selects the matching entry
from the node's configured input. It must not replace that entry with a raw
upstream quote, which can introduce numeric fields into a symbol-only contract
or override a configured order quantity. Live execution behavior is unchanged.
The regression exercises quote-to-LS-fundamentals data flow without broker calls.
Provider fixtures do not establish live data availability. The removed FMP node
is rejected at admission; its provider-specific replay adapter is also removed.
