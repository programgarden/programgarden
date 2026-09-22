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
  normalizer and result envelope; never invokes a broker transport. Special
  auction order types and modify/cancel graph adapters remain unsupported.
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

## Evidence and remaining release gates

Each validation records task/plan/workflow identity, graph/node/fixture hashes,
engine/source versions, run IDs, mode and results. Source identity covers all
engine/core/community/finance Python files and calculation dependency versions;
an editable plugin change or numpy/pandas change cannot reuse old proof.
The host persists leased
claims and checks returned identities. Final replay reloads the saved graph and
requires independent expected-output assertions; it is separate from publication.

This is an unreleased foundation. Trusted strategy-specific fixtures, complete
contract coverage, modify/cancel adapters, public
entry-path gates, queue semantics and AI tool integration remain in progress.
No new package version has been published and no incremental gate is enabled in
production. Do not describe a passing fixture as "error-free live trading".
