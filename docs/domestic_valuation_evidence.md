# Domestic position and valuation evidence

The domestic tracker retains two independent observations. The trading
cache continues to use the t0424 BEP/fill/cost request (`prcgb=2`, `chegb=2`,
`dangb=0`, `charge=1`). Reporting uses CSPAQ12300 with `RecCnt=1` and
`BalCreTp=0`, `CmsnAppTpCode=0`, `D2balBaseQryTp=0`, `UprcTpCode=0`.

- Quantity is the observed `BnsBaseBalQty`. `BalQty` can still be zero for an
  executed purchase before settlement; it must not hide that holding.
- `AvrUprc` is average cost, `PchsAmt` is acquisition amount, `NowPrc` is the
  observed quote, and `EvalPnl` is current valuation PnL. Currency is KRW.
  The CSPAQ12300 request excludes commission. t0424 `pamt` is BEP under the
  existing request, so it must not supply a field labelled average price.
- CSPAQ12300 OutBlock2 is wholly unavailable. Its zeros never supply cash,
  account assets or valuation PnL. For the explicit average-cost request,
  `PnlRat` is a fraction in the supplied example and a nonzero live response.
  Finance1.10.2 exposes percentage points only when the observed fraction
  matches `EvalPnl / PchsAmt` within six-decimal rounding. Missing, inconsistent
  or differently scaled evidence remains null. This is position valuation,
  not the account return or the return of the automated strategy.
- Both collectors read all pages with bounded, spaced continuation. Missing
  raw arrays, request-basis mismatch, absent metadata, repeated cursors,
  duplicate symbols and later-page failure invalidate the observation.
  Multiple credit lots of the same symbol currently remain unavailable;
  they are never silently overwritten or merged with a guessed cost basis.
- Missing monetary fields remain null while an explicit quantity is retained.
  Account valuation gain/loss/net requires every observed position's finite
  `EvalPnl`. A complete empty account has explicit zero valuation; a failed
  refresh has no current valuation. Trading cache retention is independent.
- `get_position_evidence()` and `get_valuation_snapshot()` return detached
  copies. Tick updates cannot turn a prior REST observation into a fresh one.
  Workflow valuation uses only the workflow's retained lots and gross basis.
  Account valuation is `source=CSPAQ12300`, `basis=broker_open_positions`,
  `commission_basis=excluded`; neither amount is realized PnL.

Read-only verification on 2026-09-15, after an owner-executed NXT purchase,
confirmed a one-share unsettled holding and different BEP/average-cost values.
The new collectors returned complete evidence without submitting an order.
The t0425 actual account response used the Korean buy label `매수`; an order
acknowledgement remains distinct from a positive SC1 or account fill record.

This does not establish FOCCQ33600 return methodology or full workflow NXT
routing/modify/cancel support. Keep actual venue metadata separate from the
fungible domestic instrument identity and preserve existing KRX defaults.

## Direct workflow nodes (engine1.38.1)

`KoreaStockAccountNode` uses the complete CSPAQ12300 position collector above,
including trade-basis quantity, observed sellable quantity and null monetary
fields. It independently obtains non-credit orderable cash from explicitly
observed CSPAQ22200 `RcvblUablOrdAbleAmt` on the example's `BalCreTp=0` scope.
Cash zero is valid; missing or failed cash never falls back to credit amounts.
Either failed query sets `balance._partial_failure`; good holdings survive a
cash-query failure. Pass the whole balance object to entry guards and sizing.
The account's scalar `pnl_rate` remains null.

`KoreaStockOpenOrdersNode` reads the exact t0425 all-orders example and filters
explicit positive `ordrem` only after bounded, complete pagination. Empty or
fully filled results are normal. Missing remaining quantity, unknown side,
duplicate pending identity or a later-page failure retains an error and must
block new entries. Instrument `exchange=KRX` stays stable across venues;
`order_venue` reports only an explicitly observed KRX/NXT value. It cannot route
a new order. An empty error result is not proof of no pending buys.

Read-only verification on 2026-09-15 observed CSPAQ family headers and terminal
`t0425.tr_cont=0` with empty header/body cursors. New node regressions use actual
response parsers, not permissive mocks that invent broker fields. No new order
was submitted for this correction.
