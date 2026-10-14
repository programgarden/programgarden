# Futures position and pending-order exchange

Status: 2.6.5 release candidate. This document does not establish package
publication or consumer deployment.

## Problem

LS CIDBQ01500 (open futures positions) and CIDBQ02400 (pending futures orders)
identify a contract by `IsuCodeVal` only. Neither detail block has an exchange
or market field; the only "exchange" fields are fee amounts. Engine 2.3.0
through 2.6.4 nevertheless labelled every futures row `"HKEX"`:
`OverseasFuturesAccountNode.positions[].exchange`, `held_symbols[].exchange`
and `OverseasFuturesOpenOrdersNode.open_orders[].exchange`.

A CME contract such as `MNQZ26` was therefore reported as `HKEX`. Workflows that
check that a held position belongs to the expected instrument (symbol and
exchange both equal, as the public beginner futures guide does) never matched,
so they could not close a CME position.

## Behaviour from 2.6.5

The exchange of each distinct contract is read from o3105 `ExchCd`, the
contract-detail TR that `OverseasFuturesContractInfoNode` already uses. The
request carries only the symbol, as in
`finance/example/overseas_futureoption/run_o3105.py`.

An answer is accepted only when all of these hold. These are the contract-info
node's identity rules, except that no expected exchange is configured here:

- HTTP 200 and no transport or parse error;
- `rsp_cd` is `00000`;
- the response block explicitly contains `Symbol` and `ExchCd`;
- the echoed `Symbol`, trimmed, equals the requested contract exactly;
- `ExchCd`, trimmed, is not empty.

The trimmed `ExchCd` becomes the row's `exchange`. In every other case, and on
timeout (20 seconds) or exception, the exchange is `None` and the node logs a
warning naming the contract. No default exchange is substituted. The position,
its quantity and the balance are still returned; only the exchange is unknown.

`held_symbols` mirrors the resolved `positions` rows one to one.

## Rate and caching

- At most one o3105 read per contract per workflow run (execution context).
  The answer is cached for the run, including an unresolved `None`, so a
  transient failure is not retried within that run; a new run reads again.
- Account and pending-order nodes in one run share the cache. Reads are
  serialized, so concurrent nodes never request the same contract twice.
- The account node reads CIDBQ01500 and CIDBQ05300 first, unchanged, then the
  missing contracts. Each o3105 read waits 2 seconds first, the gap the startup
  broker reads keep on a shared app key. o3105 is limited to 2 requests per
  second by LS.
- An empty account or an empty pending-order list makes no o3105 read. A cached
  contract costs no read and no wait.

## Compatibility

- `positions[].exchange`, `held_symbols[].exchange` and
  `open_orders[].exchange` now hold the LS exchange code (for example `CME`,
  `HKEX`) or `None`. The declared output fields are unchanged.
- A workflow that compared a CME contract with the old `"HKEX"` label no longer
  matches. Comparisons with the contract's real exchange now match.
- When the exchange is unresolved, consumers that require an exchange string
  fail closed instead of acting on a guessed exchange.
- A workflow that binds a position or pending-order row directly into a futures
  order now passes the resolved code (or `None`) as the order's exchange instead
  of `HKEX`. The order nodes themselves are unchanged in this release.
- Not changed in this release: `OverseasFuturesRealAccountNode` (its SDK tracker
  resolves exchanges separately), deep-validation fixtures, replay recordings
  and default exchange labels in futures market-data and history outputs.

## Observation

One read-only paper o3105 request for `MNQZ26` on 2026-10-15 (KST), made with a
token that already existed for a test app key (no token was issued and the
request was not retried), returned HTTP 200, `rsp_cd` `00000`, `Symbol`
`MNQZ26`, `ExchCd` `CME`, `ExchNm` `시카고상업거래소` and `CrncyCd` `USD`.
No HKEX contract was observed for this release; the `HKEX` code is the value the
LS guide and the existing contract-search node already handle.
