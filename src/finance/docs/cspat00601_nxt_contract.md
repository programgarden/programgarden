# CSPAT00601 NXT limit-order source contract

Source: LS REST stock order field table and request/response example supplied by
the owner on 2026-09-15. POST `/stock/order`, TR `CSPAT00601`, 10 requests/second.
This source is documentation evidence; this change has sent no real orders.

The input and response echo already support `MbrNo`. The shared SDK transport
serializes it unchanged for both sync and async calls. No new routing API or
default change is needed: the existing empty value keeps LS's KRX fallback.
Explicit `MbrNo="NXT"` is required for the supplied NXT example.

The confirmed example uses `IsuNo="A272210"`, `OrdQty=1`, `OrdPrc=35000`,
`BnsTpCode="2"`, `OrdprcPtnCode="00"`, `MgntrnCode="000"`, `LoanDt=""`,
`OrdCndiTpCode="0"`, `MbrNo="NXT"`. The historical symbol and price are not
current trading instructions. Six digits or an A-prefixed stock code are both
documented for live stocks/ETFs; simulation requires the A prefix. This example
does not establish NXT simulation support or all order-type combinations.

The example response echoes `MbrNo="NXT"`, returns order number 32004 and
`rsp_cd="00040"`. These establish the documented buy-order acknowledgement,
not a fill. `OrdMktCode="10"` must not be reinterpreted as the execution venue.
No SC1 venue field was supplied. Missing echoes remain unavailable: inspect
`model_fields_set`, never infer a route from a default empty value.

The owner reconfirmed that actual fills require an account query such as
CSPAQ13700/t0425 or SC1 account execution notifications. Match account/day,
order number, symbol and side; keep partial-fill quantity distinct from ordered
quantity. SC0 is order reception; S3_/K3_/NS3 are market trades, not this
account's fills. A missed SC1 message or absent first-page REST match must not
be labeled unfilled. A later read-only account query can reconcile the evidence.

## Runnable preview

From this repository with finance/core installed or on PYTHONPATH:

```sh
python src/finance/example/korea_stock/run_CSPAT00601_nxt.py
```

The command only prints the request. It does not load credentials, log in or
submit. `build_order(ls, symbol=..., side=..., quantity=..., limit_price=...)`
shows the SDK facade and returns a TR; an application's later `req()` or
`req_async()` call sends a real order. The SDK does not retry order timeouts or
transient server failures; its existing explicit invalid-token recovery remains.

Actual order validation requires owner-selected parameters, current NXT symbol
eligibility, prices/session state and an owner-executed command. NXT quote ticks
already observed through NS3 do not prove execution. Modify/cancel venue rules,
other price types and workflow-node NXT integration remain separate work.

## Discovery and directly observed quotes

The owner supplied `t9945.nxt_chk`: 1 means provided by NXT, 0 means not provided.
The supplied t8436 table has no equivalent field. `run_t9945.py --nxt-only`
filters only explicitly observed 1 values; absent/empty/unknown values remain
unknown. Direct read-only requests at 16:12 KST on 2026-09-15 returned this field
on all 4,300 master rows, including 335 KOSPI and 271 KOSDAQ rows with value 1.
These are snapshot counts, not a permanent eligible-symbol list or halt check.

A 30-symbol t8407 screen identified candidates within the account's observed
non-credit orderable amount; t8407 has no explicit NXT selector and its prices
were used only for screening. A subsequent 45-second subscription received NH1
books for 001500 and 000080 and an NS3 trade for 000080, with matching N-prefixed
venue codes. No account orders were sent. No quote for 001130 arrived in that
window; this alone does not mean it is ineligible.

The old NH1 example passed six digits, but its validator only padded that input
and omitted N. NH1 now normalizes six digits to `N` + six digits + three spaces,
preserving the same subscription key for removal/reconnect. Invalid batches are
rejected before subscription state changes.

NH1 `donsigubun="1"` was observed during the aftermarket, despite the existing
SDK's pre-open description. Do not use that enum description alone to decide
that trading is closed/open; its source reconciliation remains pending.
