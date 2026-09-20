# Session windows and guarded multi-instrument execution

`SessionGateNode` returns a decision immediately. `TradingHoursFilterNode` is a
waiting filter; choose it when waiting until opening is intended. SessionGate
uses its own current UTC clock converted through an IANA timezone. It does not
accept a workflow-controlled clock or bypass the decision in dry-run mode.

```json
{
  "id": "session",
  "type": "SessionGateNode",
  "timezone": "America/New_York",
  "windows": [{"start": "09:35", "end": "15:50"}],
  "days": ["mon", "tue", "wed", "thu", "fri"],
  "closed_dates": []
}
```

Connect `session` to an `IfNode` comparing `{{ nodes.session.allowed }}` with
`true`, then connect only that node's `from_port="true"` to the guarded work.
An ordinary edge does not interpret a boolean output. `local_date` is available
even when blocked and can anchor completed-bar analysis outside trading hours.

A window includes its start and excludes its end. Multiple windows represent
breaks. In an overnight interval, times after midnight belong to the opening
weekday. Either a matching local date or opening date in `closed_dates` blocks
the interval. IANA timezone data handles DST; it is not an exchange holiday or
halt calendar. Operators must maintain those exclusions or add an authoritative
market-status source. Recheck the window immediately before an order because
analysis/API work can cross the end boundary.

## Split routing

Use `SplitNode.array` explicitly and pair it with a reachable `AggregateNode`.
`items` is an output port, not an input setting. Account outputs contain several
arrays, so name the intended array rather than relying on dictionary order.

Each Split item now obeys its own IfNode true/false routing. A blocked item skips
its downstream side effects and does not reuse the preceding item's output.
An active alternative remains eligible for collection when its sibling is skipped.
A false outer gate skips the Split handler itself. These rules apply to scheduled
re-execution as well as a new one-shot job.

Branch expressions currently share execution context. Consequently, branches
containing IfNode or an order node execute sequentially even if `parallel=true`
was requested; a warning records the effective behavior. Other parallel branches
retain their existing behavior. Prefer sequential processing for trading and
use `delay_ms` to respect shared broker rate limits.

## Duplicate submission and evidence

A branch decision alone is not a durable order reservation. Strategies should
validate positions, pending orders, matching quotes and cash/contract capacity,
and commit a unique strategy/instrument/signal reservation before submission.
Only the successful first reservation may follow the order path. Do not release
it automatically after rejection, timeout, unknown acknowledgement or a later
closed time gate: reconcile broker state before a deliberate retry.

Use durable storage scoped to the intended account and workflow. Independent
files, workers or strategies do not provide distributed exactly-once submission.
Broker acknowledgement does not establish a fill. A limit order, including a
position-reduction attempt, does not guarantee execution.

## CodeNode bindings

CodeNode inputs and outputs must contain finite JSON values. A helper expression
such as `{{ nodes.select.symbols.count() }}` yields a number; passing `.count`
without calling it yields a method and is rejected before worker dispatch.
CodeNode still executes in a separate credential-free subprocess. Provider keys
belong to credential-backed nodes, not CodeNode inputs or prompts.
