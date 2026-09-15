# Open-position valuation outcomes

Engine 1.37.9, core 1.28.2 and finance 1.9.8 add optional
`WorkflowPnLEvent.account_valuation` and `workflow_valuation`. They are independent
of realized `personal_metrics` and do not change trade counts or order behavior.
Older records are not backfilled.

Both envelopes have `version=1`, `product=overseas_stock`, an ISO UTC
`observed_at`, a `basis`, and `groups` containing `currency`, positive `earned`,
positive `lost`, and signed `net=earned-lost`. Distinct currencies remain separate.
None means unavailable; an explicitly empty workflow group list means no retained
open workflow positions. An account with complete, zero-valued currency rows can
report zero in those currencies without inventing a default currency.

## Account source

The SDK captures COSOQ00201 during its existing position refresh. It reads
OutBlock4.FcurrEvalPnlAmt by CrcyCode and separates positive/negative values.
The group net must reconcile with OutBlock3.FcurrEvalPnlAmt within the supplied
four-decimal amount precision. This is `basis=broker_open_positions`,
`source=COSOQ00201`; no fee inclusion rule is inferred. The timestamp is when the
response was observed, not a broker trade timestamp or a promise of a fresh quote.

The existing example request remains RecCnt=1, BaseDt=<query date>, CrcyCode=ALL,
AstkBalTpCode=00. No additional TR, OAuth, order or retry is introduced.
Complete HTTP/response/continuation metadata, a matching date/currency/balance
echo and explicitly present amount/unit fields are required. The response parser
retains private block-presence evidence so omitted blocks cannot become apparent
empty success through Pydantic defaults. Missing/partial/failed observations and
inconsistent/duplicate rows yield None. Failed refreshes invalidate this summary
without deleting the existing trading-position cache.

The broker summary is copied on read and stays independent of the SDK's mutable
tick-based fee estimates. Its original observation timestamp survives forwarding.

## Workflow source

`basis=workflow_open_positions_gross` uses the existing retained workflow position
cost and current-price calculation. Each position needs an explicit currency from
the matching account position; model-default USD is insufficient. Missing price,
cost, attribution, currency or a contradictory amount yields None. Account
positions never become workflow-owned positions by implication.

The fields are appended to the core event to preserve previous positional
constructor arguments. The engine dependency floors require the core event
fields and the finance snapshot method together. Workers and desktop consumers
must forward the optional fields immutably before the UI can display them.

## Scope

These are current holdings valuations, not historical realized gains, total asset
returns, cash-flow-adjusted TWR or MDD. Futures and domestic stock collection remain
separate work. Public projections expose only currency summaries, never the raw
account response or account-only symbol identities.
