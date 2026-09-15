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
