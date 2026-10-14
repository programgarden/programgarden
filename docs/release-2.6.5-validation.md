# Version 2.6.5 release candidate validation

The candidate is based on merged upstream 2.6.4 (`45ff52a6`). It prepares
engine 2.6.5 only; core 2.6.2, finance 2.0.2 and community 2.3.1 are unchanged,
and so are the engine's dependency requirements. The root and engine lock files
need no change and `poetry check --lock` reports both as fresh. This document
does not establish package publication or hosted installation.

The [futures position exchange correction](futures-position-exchange.md)
describes the change. OverseasFuturesAccountNode positions and `held_symbols`
and OverseasFuturesOpenOrdersNode rows take their exchange from o3105 `ExchCd`
instead of a fixed `HKEX`. An answer without exact evidence leaves the exchange
`None`. Each run reads o3105 at most once per contract, shares the answer
between nodes and spaces reads 2 seconds apart. The release contains only this
correction.

Local Python 3.12 verification used a fresh virtual environment with the
candidate source packages installed in editable mode:

- 22 new offline cases use real SDK models (CIDBQ01500, CIDBQ05300 and
  CIDBQ02400 envelopes parsed by their SDK TR classes, o3105 bodies parsed by
  `TrO3105`). They cover resolved CME/HKEX positions, `held_symbols` and
  pending orders; blank, missing, mismatched, rejected, HTTP-failed, raised and
  timed-out o3105 answers (`None`, never a default); one read per contract per
  run including unresolved answers; concurrent nodes sharing one read; the
  2-second gap before each read and none for cached or empty results; the
  execution-context cache; the identity rules; and the actual `LS` client with
  only the HTTP transport replaced, which sends `{"symbol": "MNQZ26"}`.
  15 of them fail against the unchanged 2.6.4 executor.
- The output-schema contract now reads `held_symbols` from its list
  comprehension; the declared fields are unchanged.
- 723 focused cases in 34 modules covering futures and stock account, pending
  order, broker evidence, paper business date, replay snapshot and output-schema
  tests passed (23 skipped).
- The complete engine suite reported 3410 passed, 25 skipped, 3 xfailed and
  5 failed. The same 5 cases (three cancel-order port assertions and two replay
  cases) fail identically on the unchanged 2.6.4 source (3388 passed) in the same
  environment and do not involve the changed modules.

Offline, the shipped beginner futures guide's signal code with a CME `MNQZ26`
position reached its sell decision with the candidate, where 2.6.4 raised
`Ambiguous instrument position`. With an unresolved exchange it still raises,
which is the intended fail-closed result.

One read-only paper o3105 request for `MNQZ26` used a token that already
existed in the development token store for a test app key. No token was issued
and the request was sent once without retry. It returned HTTP 200, `rsp_cd`
`00000`, `Symbol` `MNQZ26` and `ExchCd` `CME`. No order, account change or other
broker request was made. No HKEX contract was observed for this release.

No wheel or sdist was built for this preparation. The release owner builds the
reviewed merged main commit, inspects the artifacts, publishes the engine only
and tags that commit. Core, finance and community are not rebuilt or published.
Package publication, clean index installation, consumer adoption and desktop
packaging remain separate release steps.
