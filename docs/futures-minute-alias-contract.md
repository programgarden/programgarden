# Futures minute aliases: 2.6.2 release candidate

Based on public main 8c598674 (engine/core 2.6.1). This is a local review
candidate, not a published 2.6.2 release or consumer rollout.

The workflow catalog exposed `1m`, `5m`, `15m` and `1h`, but the executor
recognized only the legacy minute names. Canonical minute requests silently
selected daily o3108 data while keeping the requested minute label. Canonical
`1m`, `5m`, `15m` and `30m` now select the same existing o3103 requests as
`1min`, `5min`, `15min` and `30min`. The existing `30s` request is also retained
and exposed in the catalog. Daily `1d`, weekly `1w` and monthly `1M` keep their
o3108 selectors and request dates.

No confirmed ncnt=60 contract was found. `1h`, `3m` and unknown periods therefore
raise `UNSUPPORTED_FUTURES_HISTORY_INTERVAL` before credential access or deep
fixtures; static validation reports `INVALID_FIELD_ENUM` at `interval`. No period
is silently replaced with daily or one-minute data. Native saved workflows using
known legacy minute aliases remain valid. Authoring catalogs continue to expose
canonical names; use these when authoring a new graph.

## Existing one-page boundary

The minute reader still makes one o3103 request per symbol with `readcnt=200`
and empty initial continuation fields, including when the response reports more
data. This is an application request size, not a confirmed LS maximum. It does
not follow the complete continuation chain or require that chain to end within
a new page/deadline budget. Sorting returned bars oldest-first does not imply
any guarantee about server page order.

The response shape is unchanged. Minute start/end dates are not sent to o3103;
the output `period` echoes the requested dates and is not a coverage receipt.
The initial page is not promised to cover that entire range, contain a guaranteed
latest-N set, or contain only completed bars. No time-zone, retention horizon,
continuous-contract, complete lookback or missing-bar guarantee is added. Consumers
must establish required evidence before interpreting an order signal. No internal
database fallback or new `allow_partial` switch is introduced.

This deliberately separates the reproduced wrong-period defect from range and
pagination design. The SDK's actual o3103 example and blocks require initial
empty `cts_date`/`cts_time`; continuation helpers copy broker-returned keys.
The [official LS detail](https://openapi.ls-sec.co.kr/guide/api/6ds88k84-z7x1-5t7b-0aj8-13ormd5084iu?type=rest&api=906d2d0a-7a6d-4ecc-b574-ca2154a70bca)
contains a descending two-row response example but no universal cross-page
ordering or range cutoff contract. An older timestamp is not a justified early
stop rule. Efficient complete-range queries remain separate work.

## Adjustment compatibility

Previously `adjust=True` was advertised as rollover-adjusted history, but it
reached the same unadjusted exact-contract fetch as false. It now raises
`FUTURES_HISTORY_ADJUST_UNSUPPORTED` before credentials or deep fixtures, and
static validation reports `INVALID_FIELD_ENUM` at `adjust`. No automatic rewrite
of a saved true value occurs.

Explicit false and omission remain valid. The Pydantic model declares
`Literal[False]`; the boolean FieldSchema is retained with default/example false,
fixed-only mode and truthful help. This keeps it discoverable to tool/catalog
consumers instead of deleting a saved field. Native validation enforces the
restriction; the existing UI checkbox is not claimed to be a read-only control.
No rollover stitching or price adjustment was implemented.

## Local validation and release impact

Focused tests cover canonical/legacy request identity, one call despite more
available data, unchanged output sorting/shape and requested-period labels,
unchanged daily/weekly/monthly requests, pre-credential unsupported errors,
static/deep validation, adjustment compatibility and localized schema fields.
Existing stock interval and symbol-iteration tests remain included. All broker
responses are synthetic; no broker or customer account was accessed.

The private AI consumer was inspected separately using this exact native source:
canonical fields/adjustment restrictions enter its native catalog and structural
validation, and its current 270 private source graphs and skeletons were checked
offline. No private strategy source is copied into this public repository.
Database publication, embedding and live model acceptance are separate gates.

Core and engine prepare version 2.6.2 together; the engine requires core
^2.6.2. The candidate engine lock records the locally built core artifacts;
publication must verify their exact hashes against the merged-source build and
the actual published distribution before engine publication. Finance, community
and consumer requirements are unchanged. The prepared 2.6.1 adoption packet is
preserved as historical evidence, not as proof for 2.6.2. Its changed implementation has a different
runtime identity: a 2.6.1 image receipt or skeleton stamp cannot certify it.
Choosing a later combined consumer rollout requires fresh exact image/dependency
proof, native catalog/skeleton revalidation and actual dev acceptance.
