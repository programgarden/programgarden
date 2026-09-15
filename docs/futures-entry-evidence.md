# Futures entry evidence

Engine 1.39.1 fixes the capacity node's credential lookup. A real paper-account
preflight found that 1.39.0 read only a direct secret alias, although production
hydrates the workflow credential list and the broker also stores an exact
broker-scoped secret. Capacity now uses the shared exact-futures resolver:
workflow list/dict credentials and the selected broker's secret work; unrelated
direct/product slots, wrong modes/types and ambiguous references do not. Tests
use actual ExecutionContext instances instead of a permissive credential mock.
The unchanged generated draft then reads capacity 43 and reaches a single
intercepted one-contract order. No paper or live order was submitted in that
preflight. The owner selected paper-futures verification and deferred live
futures trading; matching paper acceptance/fills remain a separate checkpoint.

Engine1.39.0, core1.30.0 and finance1.10.3 address failures observed in a real
chatbot-generated HKEX paper draft. The original graph passed a skipped-branch
dry run but could not reach a valid entry: a bare market symbol, the unavailable
singular `value` port, missing tick metadata, a cash-versus-quote margin check,
and unsupported `IfNode.operator=is_true` each obscured the intended behavior.

`OverseasFuturesMarketDataNode.symbol` takes the full `{symbol, exchange}`
identity. Consume its `values` array, selecting one exact identity. `tick_size`
is the explicitly observed positive finite `o3105.UntPrc`; absent or invalid
ticks stay null. Quotes with unavailable/mismatched broker identity or price
are not relabeled as the requested contract.

`OverseasFuturesOrderableQuantityNode` queries CIDBQ01400 with `symbol`,
`side`, `order_type`, `price` and `query_type` (`new`, `close`, `total`). It
inherits the workflow's selected futures broker. Outputs are `quantity`
(integer or null), `verified` (boolean), and `error` (string or null). Require
verified=true and enough quantity for the eventual order; bind the same
contract, side, type and price. The query makes no order or reservation. The
deep-validation fixture is virtual, not evidence of real margin capacity.

CIDBQ01500/02400/05300 account readers require a matching, explicitly observed
terminal response. Missing arrays, broker/HTTP failures and continuation pages
cannot authorize entry. The SDK preserves array presence in `model_fields_set`.
An observed 00707 empty result is normal only for matching position/pending
queries. Unknown pending identity, side or quantity is an error. Consumers
must retain account `balance._partial_failure` and pending `error` signals.
Existing account currency aggregates are retained for compatibility; they do
not determine contract capacity and must not be summed for that purpose.

On2026-09-16, read-only HKEX paper probes returned o3105 price/tick fields and
CIDBQ01400 `OrdAbleQty=43`. The price echo was a decimal string numerically
equal to the requested price. Position/pending responses were explicit empty
00707 terminal results, and CIDBQ05300 returned five currency rows with00136.
These observations establish read contracts, not real order acceptance/fills.
No real or paper order was submitted by these probes.

Validation covers actual SDK parsing, absent/zero/mismatched capacity, price/tick
identity, failed account evidence, unsupported If operators, registry/locales
and existing offline fixtures. The repaired chatbot reference also exercises
23 positive/blocked cases with network forbidden and the order boundary
intercepted. Nonempty live-futures fills and broker overnight-day semantics
remain separate checks; an older signed desktop/worker must be upgraded before
using the new node.
