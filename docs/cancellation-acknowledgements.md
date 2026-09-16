# Cancellation acknowledgement and completion

Author: Codex, 2026-09-16. Status: source-only P4 checkpoint, not released.

The stock, futures and domestic CancelOrder executors return acknowledgements.
A positive cancel-order number does not establish that the original remainder
was cancelled. The result now preserves the legacy keys while distinguishing:

- `cancel_result.success: true`: submission was acknowledged, not completed.
- `cancel_result.status: accepted` and `confirmation_pending: true`.
- `cancel_result.order_id`: the original target; `cancel_order_no`: the new request.
- `cancelled_order_id`: retained legacy alias for the original target.
- `cancelled_order.status: cancel_requested`, replacing the premature `cancelled`.

Reject missing, zero, negative or nonnumeric acknowledgement numbers. No request
parameters, automatic retries, live ownership or execution-state mutation changes.
Clients must use matching broker completion evidence to establish cancellation.
A missing pending row alone can mean a fill and must not establish cancellation.
Partial fills remain positions; cancelling the remainder creates neither a sale
nor realized profit. Historical partial-cancel recovery remains held until its
quantity semantics are verified. The owner's full-fill and no-fill-cancel probes
do not prove the missing partial-fill case.

Node metadata exposes the actual acknowledgement fields and no longer teaches
immediate cancellation-to-replacement execution. Two examples per product remain,
including a clearly illustrative explicit target requiring owner/account checks.
The compatibility ID port is relabelled as the cancellation target. Existing
saved user graphs are not rewritten. Updated core metadata must be published and
then synchronized/reseeded into pg-ai together with the corresponding runtime;
do not seed a contract that deployed engines do not yet produce.

The earlier bulk-helper stub has been replaced by the verified owned-stock
adapter described below. Emergency market liquidation remains excluded and
explicitly reports that it is unimplemented. Futures/domestic bulk cancellation
is not enabled by the presence of their existing individual cancel nodes.

Validation: 52 focused executor, real SDK field-contract, metadata and locale
checks plus six schema/example cases pass. Broker calls are intercepted; no real
order, cancellation, credential login or active workflow change was performed.
# Owned pending-order action (source checkpoint)

`await job.cancel_pending_orders()` requires a paused, quiescent, execution-scoped
overseas-stock job and its exact product credential. It reads complete fresh
broker evidence, matches date/order/symbol/side/venue against the owned ledger,
and excludes manual or other executions' orders. Each request is journalled before
the broker call; timeouts and explicit repeated calls cannot resend it. Up to20
targets and a120-second operation deadline bound the work.

The result separates `requested_orders`, `cancelled_orders`, `filled_orders` and
`pending_orders`, each identified by order date and number. Terminal status needs
the previously verified full-fill or wholly unfilled cancellation evidence.
Missing reads and historical partial-cancel chains return confirmation pending.
No position is sold, and this operation does not fabricate fills or PnL. Restart
must perform the normal fresh account verification before strategy execution.

The synchronous `cancel_all_orders` wrapper dispatches onto the existing job loop;
async callers use the job method. Stop remains separate and sends no broker order.
Paused main/event loops now observe stop without running queued strategy nodes.

84 focused cancellation and actual-lifecycle tests pass with broker transport
intercepted. This is unpublished engine source. Futures/domestic bulk actions,
host/UI controls and durable adjustment display remain separate integration gates;
existing explicit product CancelOrder nodes retain their accepted-request outputs.


## Managed client routing (2026-09-16)

`cancel_all_orders_async(job_id, executor=pg.executor)` uses exactly the supplied
client and its current event loop. The synchronous wrapper accepts the same
executor for worker-thread callers and dispatches to the owning active loop.
Neither wrapper searches other clients or accounts. Omitting the executor retains
the legacy tools singleton, which cannot find jobs created by `ProgramGarden()`.
Managed hosts can instead call `await job.cancel_pending_orders()` directly.
Seventeen routing/owned-cancellation tests cover same-named jobs in separate real
clients, wrong-loop refusal, thread dispatch and the existing broker-bound guards.
The owner approved overseas-stock UI support first; futures/domestic follow
verified terminal evidence.

## Managed stock stop control

The owner approved overseas stocks first; futures and domestic bulk controls wait
for verified terminal evidence. This does not remove existing cancel nodes.
`managed_order_control.pause_and_cancel_owned_orders` validates the exact managed
execution key before pausing. It drains active nodes for at most ten seconds and
then calls the existing journalled adapter. The whole operation is bounded at
135 seconds; a regular host stop interrupts it. The host owns final shutdown on
success, failure or cancellation. Resuming the same job is prohibited; a fresh
start must verify the account again. Ordinary stop never sends a broker cancel.

This module is an opt-in integration seam for worker/tray controls. Its presence
alone does not enable a UI, change an installed runtime or start trading.
