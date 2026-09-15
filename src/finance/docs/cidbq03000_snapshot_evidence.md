# CIDBQ03000 deposit/balance snapshots

The supplied LS contract names this TR overseas futures deposit/balance status.
`AcntTpCode="1"` selects a consignment account. `TrdDt` is the requested trading
date. The repository example `example/overseas_futureoption/run_CIDBQ03000.py`
uses a paper account with `RecCnt=1`, `AcntTpCode="1"`, and `TrdDt=""`.

## Observed paper responses, 2026-09-09

Two read-only requests used that same SDK query builder and the platform's shared
token provider. No order or independent OAuth request was submitted. The blank
date request completed at18:46:13 KST; the `20260908` request at18:46:14 KST.
Both returned HTTP200, `rsp_cd="00136"`, and the original message
`모의투자 조회가 완료되었습니다.`. Both parsed as five balance rows.

The blank request retained blank dates in the echo and each row; do not replace
those fields with a purported broker-confirmed date. The dated request echoed
`20260908`. USD, JPY, HKD, CHF and CAD rows were returned. No aggregate target was
returned in these two responses; the separately supplied LS example has `TOT(USD)`.

| HKD field | Blank date request | `20260908` request |
| --- | ---: | ---: |
| `OvrsFutsDps` | 999840.00 | 999840.00 |
| `CustmMnyioAmt` | 0.00 | 0.00 |
| `AbrdFutsLqdtPnlAmt` | 0.00 | 0.00 |
| `AbrdFutsCmsnAmt` | 40.00 | 0.00 |
| `PrexchDps` | 999800.00 | 999840.00 |
| `EvalAssetAmt` | 998910.00 | 999840.00 |
| `AbrdFutsEvalPnlAmt` | -890.00 | 0.00 |
| `LastSettPnlAmt` | 0.00 | 0.00 |

For this observed HKD snapshot, `999840 - 40 = 999800` and
`999800 - 890 = 998910`. The change from the dated snapshot's evaluated assets is
`-930`, matching the observed commission and valuation loss. Adding those
components again to `EvalAssetAmt` would double count them in this example.

This establishes a working date-specific query and the stated numerical
relationships in these responses. It does not establish a universal accounting
formula, historical retention, intraday reset boundary, or the inclusion of
commission/final settlement in liquidation P&L: both liquidation and final
settlement values were zero. It is not a verified contest return or MDD.

## Owner-confirmed daily cash-flow scope, 2026-09-15

The owner confirmed that `CustmMnyioAmt` is the net customer deposit/withdrawal
amount for the current business day, not a cumulative account balance. Preserve
this fact for this TR; generic fields named `ioAmt` in other TRs are not evidence
of identical semantics. Other suggested cash fields must be checked against
their own actual models before use.

Repeated intraday observations of500 describe the same daily net flow; they
must not be summed into1000. A following business day's0 is a daily reset,
not evidence of a500 withdrawal. Snapshot observation timestamps are not
individual flow timestamps, and calendar midnight does not establish the
broker's business-day boundary. A blank returned `TrdDt` remains unknown.
The existing dated paper responses contain zero flows and do not independently
verify how nonzero historical cash flows are represented.

## Unreleased account snapshot collector

`FuturesAccountTracker.get_account_snapshot()` returns an isolated copy of the
latest supported observation from its existing CIDBQ03000 refresh. No extra
request is added. It clears supported evidence on a failed/partial refresh;
the legacy balance/position caches retain their existing behavior.

The additive envelope carries source, observation time, requested/returned
dates and `cash_flow_basis="business_day_net"`. Each row retains its
`currency_target`, separate native/aggregate classification and explicit
`equity`, `daily_net_cash_flow`, `unrealized_pnl`, and `margin` amounts.
Missing optional amounts remain null. Missing equity, malformed numeric data,
contradictory dates, duplicate currency targets, errors and continuation pages
do not produce a supported snapshot. Raw whitelisted fields preserve decimal
precision before the legacy float models; no account number/password is copied.

`TOT(USD)` and native currency rows must not be added together. Reported
`EvalAssetAmt` already includes its valuation components; do not add unrealized
PnL or fees again. This collector does not reconstruct gross gains/losses,
workflow ownership, historical flows, adjusted return percentages or MDD.
The engine forwards observations through optional account event envelopes.
Application persistence and estimated returns are separate consumers; this
SDK does not calculate account returns.

With `capture_daily_snapshots=True`, the tracker additionally requests the
current KST calendar date and previous date at most once every 300 seconds,
spacing the two requests and limiting each to 30 seconds. The default is false
for existing SDK callers. `get_daily_account_snapshots()` returns an isolated
version1 batch with `source`, UTC `observed_at` and two
`entries:[{requested_date,snapshot}]`. Failed/unsupported queries retain null
snapshots. This opt-in collector adds two queries; the ordinary getter does not.
Explicit date echo and row validation are mandatory; KST is only a way to choose
query dates, not proof of broker business-day boundaries.

Read-only paper queries on2026-09-15 for20260914 and20260915 each returned their
requested date with CAD/CHF/HKD/JPY/USD rows, all with zero net flows. No orders
were placed. These observations establish date query support, not actual
nonzero deposit/withdrawal behavior.

A read-only paper query on2026-09-15 returned HTTP200, rsp_cd00136 and five
currency rows. Its response header uses the family code `tr_cd="CIDBQ"`,
although the request and payload blocks are explicitly CIDBQ03000. Accept
that observed header as well as the full code only with the exact typed
CIDBQ03000 payload/echo checks. Unrelated payload block names still fail.

## Field metadata corrections

The supplied table specifies `OvrsFutsDps` as23.2 and the other monetary fields
as19.2, `CrcyObjCode` length12, date length8, account number length20 and password
length8. These are wire metadata, not new runtime validation constraints.
`LastSettPnlAmt` is labelled final settlement P&L (`최종결제손익금액`); the former
description “last daily settlement” asserted more than the supplied label.
Keep native currency and aggregate rows distinct, and preserve missing raw
fields before typed defaults when deciding whether financial evidence exists.
