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
