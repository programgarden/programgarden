# NS3 NXT trade-tick contract

Source: LS contract copied by the owner on2026-09-15 and a45-second read-only
subscription on the same date.10 actual ticks contained all27 tabulated fields
plus `high`; all values arrived as strings. This verifies quote delivery only.
No SC1 account fill arrived and no order was placed.

`Real.NS3()` / `Real.NXT체결()` exposes subscription/listener methods matching
other realtime clients. Subscription uses `tr_type="3"`; removal uses `"4"`.
The source key is `N010950   `: N plus six digits plus three spaces. The client
also accepts the seven-character prefixed form and normalizes before retaining
reconnection keys. Invalid batches are rejected before subscription mutation.
No symbol eligibility, order routing or execution venue is inferred from it.

The field table declares numeric values, but the source example and live ticks
send strings. `hightime` is declared Number8 while the example is `"080908"`;
clock strings retain leading zeros. `high` is absent from the table but present
in its example and actual ticks. Each field preserves source type/length metadata.
Missing values remain None and `model_fields_set` records actual presence;
unknown extra keys survive parsing. Zero is distinct from missing.

Do not reuse S3_ status/sign enums, the cumulative-value unit or trade-strength
formula: the supplied NS3 source does not state them. `exchname` describes the
quote venue and cannot establish the execution venue of an account fill.
The runnable example is `example/korea_stock/real_NS3.py`; it only subscribes and
returns field-presence/count evidence, without logging credentials or prices.

## SDK live recheck

On2026-09-15 06:44:25–06:45:10 UTC the new shared SDK client subscribed
using the exact source request. LS acknowledged00000 and delivered one actual
tick with all28 fields, with zero parse errors. The example then unsubscribed
and closed the socket.39 source/socket tests passed; after public exports and
regression checks,145 tests passed. No broker order was submitted.
