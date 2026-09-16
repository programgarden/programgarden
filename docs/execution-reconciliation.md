# Execution reconciliation foundation

Status: source-only P4 checkpoint, not a published runtime release.
Author: Codex, 2026-09-16.

## Runtime storage contract

`ProgramGarden.run`, `run_async`, executor execute/restore and checkpoint tools
accept an optional `execution_key`. It is a host-owned, globally unique identity
for the project and account execution, never an editable DSL field. The same
key resumes the same SQLite file after DSL/job ID changes. A different account
execution uses another file; old files are preserved. Legacy callers retain
their previous filename and behavior when the argument is absent.

Scoped positions, risk state and checkpoints share a filename derived only
from the SHA-256 hash of the key. The ledger binds the key, product, provider and
paper/live mode and rejects mismatches. Invalid keys fail before execution.
Worker/tray adoption of an existing legacy database is **not implemented**.
Do not switch deployed hosts to this argument until migration is verified.

## Verified adjustment boundary

The scoped BrokerNode reads complete, fresh broker holdings and pending-order
evidence before strategy execution. Missing raw blocks, rejected queries,
continuation, dropped parser rows, missing quantities, wrong query scope and
ambiguous identities hold startup. A changed fill revision also invalidates the
snapshot. Broker calls in the tests are intercepted; no real orders are sent.

Only a reduction of existing workflow-owned lots is allowed. Broker excess is
never imported. The FIFO reduction and its basis audit commit together; failure
rolls both back. No synthetic trade_history row, realized profit, win or fill
notification is created. An actual adjustment emits `position_reconciled` via
the existing risk-event listener; no change emits no event. SQLite adjustment
history is implemented, but cloud persistence and the user-facing history are
still pending.

Scoped manual/other fills consume only non-workflow lots. This prevents a late
manual sell from applying an already observed startup reduction twice. External
changes to owned lots require a new verified reconciliation. Legacy behavior
remains unchanged. Scoped cancellation notifications retain order ownership so
a late partial fill cannot lose attribution; final cancellation reconciliation
is not yet implemented.

## Missing fills: unresolved recovery policy

A fully or partly missed sell must be reconciled before trimming. An incomplete
owned order, historical fill without an execution identity, executable owned
order or conflicting fill evidence currently holds startup. A manual pending
order also blocks a reduction of that instrument. Absence from a pending-order
list is not proof that an order was cancelled. These conservative holds are
intentional; they are not a completed recovery implementation.

The owner reports that no historical overseas-stock individual execution-number
TR could be found. COSAQ00102 supplies order-level quantities and average prices;
AS1 supplies individual execution identity live. Do not invent a historical
execution number or treat an order total as a new individual fill.

Proposed, **not approved or implemented**: recover confirmed order-level totals,
mark derived PnL as estimated, exclude recovered aggregates from individual-fill
and win-rate statistics, and prevent overlap with later live execution events.
The owner requested an explanation of this proposal; that request is not approval.
Amend/cancel chains, partially filled orders, cross-day dates and replay overlap
must be verified before enabling recovery. Unknown evidence keeps execution held.

## Remaining integration gates

- Obtain the owner's recovery-policy decision; implement that policy separately.
- Preserve and verify legacy DB ownership before worker/tray storage adoption.
- Complete explicitly owned pending cancellation; distinguish submission from
  confirmed outcome. Emergency market liquidation remains excluded.
- Persist and render the adjustment history with brief localized notifications.
- Review recovery/subscription ordering and late-event races end to end.
- Keep futures short-position accounting distinct from the existing buy-lot FIFO;
  the current adapter must not net shorts into available long quantity.
- Run integrated dev verification before PyPI and runtime pin updates; native
  builds remain last. This checkpoint changes no published version or live job.

## Validation

333 focused tests pass: scoped SQLite storage, rollback and identity, missing and
partial sells, late external fills, SDK response contracts, startup notification,
checkpoint, execution deduplication, broker shutdown and futures order lifecycle.
The expanded run exposed nine pre-existing lifecycle fixture failures at clean
baseline `d62dc5c`; the same failures reproduced in an isolated worktree. Fixtures
now include the current futures balance hook and domestic/futures snapshot methods.
No real broker transport, production mutation, cancellation or workflow restart
was performed for this checkpoint.
