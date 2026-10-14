# Paper futures current-day query compatibility

Status: local candidate; no package release or deployed runtime acceptance is
established by this document.

The published CIDBQ02400 guide says that same-day mode (`ThdayTpCode="1"`)
uses blank start/end dates. The matching SDK example includes explicit dates in
that mode. An observed paper response rejected blank dates with `03139` and a
request for a start date. Adding `RecCnt=1` alone did not resolve the rejection.
Using the explicit `CIDBQ01500OutBlock1.QryDt` from a fresh current inquiry did.
This is a paper compatibility observation, not a universal amendment of the
published TR contract or proof that every account/filter behaves identically.

The engine's paper startup snapshot reuses its current CIDBQ01500 positions
response. Paper OpenOrdersNode and legacy post-ACK fill observation make one
fresh CIDBQ01500 read before CIDBQ02400. The current query keeps the SDK example
filters (`RecCnt=1`, `AcntTpCode="1"`, `FcmAcntNo=""`, `QryDt=""`,
`BalTpCode="2"`). Only a valid, explicitly returned YYYYMMDD and nonempty account
echo may supply the two order-query dates. No local date, previous-day guess,
persisted cache or expanded history window substitutes for missing evidence.

The observation is tied to the same LS token-manager identity, app-key
fingerprint and paper mode. Those must remain unchanged before and after both
reads, and the request pair expires after 60 monotonic seconds. The order echo
must match the original account, both dates and every non-count query filter.
Startup position quantities, pending-order identities and the existing read
guards remain required. Credential values and account echoes are never logged.

Observed `02679` with the exact empty-response message is accepted only by this
paper path when raw summary/detail blocks, explicit empty rows, terminal
continuation and exact query scope are present. Missing blocks, unknown messages,
partial pages and rejections remain unavailable. Startup stays held; the pending
node returns an explicit error; best-effort fill observation does not assert a
fill. No order is submitted, retried or canceled by this adapter. Managed futures
lifecycle hosts continue to own their separate canonical fill reads.

The SDK's existing per-TR rate limiter remains responsible for request pacing.
Startup introduces no extra positions request. Each paper pending/fill inquiry
adds one current positions read; there is no automatic retry in this adapter.
Live-account paths are unchanged. Direct low-level TR clients retain control of
their request dates and should consult the [published/observed contract](../src/finance/docs/cidbq02400_contract.md).

Offline tests exercise real SDK response models, midnight-date independence,
complete empty results, partial fills, changed key/mode/account, stale dates and
missing/partial responses. The incident's live verification covered pending
orders with `OrdStatCode="2"` and `QryTpCode="1"`. Startup/OpenOrdersNode preserve
their existing `QryTpCode="2"`; fill observation preserves `OrdStatCode="0"`.
Those filter variants are tested offline, not claimed as newly live-verified.

## Account node and rejection messages (2.6.4 candidate)

OverseasFuturesAccountNode reads CIDBQ01500 with the existing explicit
`QryDt` request. Before this candidate it rejected the paper empty-account
answer (`02679` with the exact empty-result message), so a paper account with
no positions returned an error and an empty output. For a paper client only
(`token_manager.paper_trading is True`), that answer is now a complete empty
result when explicit empty rows, terminal continuation and the full query echo
are present. Live clients, other messages, nonempty rows, partial pages, echo
mismatches and other TRs (including CIDBQ05300) remain errors. The request is
unchanged. The explicit-date form of this answer was not separately observed;
only the exact envelope is accepted, so a different paper answer stays an error.

OpenOrdersNode and legacy fill observation already use the paper path above for
both CIDBQ01500 and CIDBQ02400 and needed no change.

An unaccepted response code now names the broker's own message, using the same
text as the server preparation gate:

```
<TR>: unverified_response_code=<code> rsp_msg=<message>
```

The prefix up to the code is unchanged, so readers matching the previous text
still match. The message is bounded to 80 characters; control and format
characters become spaces and outer whitespace is removed. The futures account
and live pending-order reader reports an unaccepted code the same way instead
of the generic "did not return a complete terminal response". Missing blocks,
partial pages and echo mismatches keep their existing reasons, and a missing
block can still hide the broker's code in the startup reader.
