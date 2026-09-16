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

`cancel_all_orders` still has no verified owned-order adapter. It now explicitly
returns `status: not_implemented`, rather than an apparently successful empty
result. Bounded owned-order submission, terminal confirmation, persisted history
and host/UI integration remain open. Emergency market liquidation stays excluded.

Validation: 52 focused executor, real SDK field-contract, metadata and locale
checks plus six schema/example cases pass. Broker calls are intercepted; no real
order, cancellation, credential login or active workflow change was performed.
