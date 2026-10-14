# Version 2.6.6 release candidate validation

The candidate is based on merged upstream 2.6.5 (`28fa1f41`), which already
contains the [futures position exchange correction](futures-position-exchange.md)
([2.6.5 validation](release-2.6.5-validation.md)). It prepares engine 2.6.6,
core 2.6.3 and finance 2.0.3; community 2.3.1 is unchanged. The engine now
requires core ^2.6.3 (ranking node classes) and finance ^2.0.3 (g3112).
Finance 2.0.3 and core 2.6.3 are published (see "Publication" below) and the
engine lock pins their published files. This document does not establish
engine publication or hosted installation.

The changes were first prepared on 2.6.4 (`45ff52a6`) and then rebased onto
2.6.5. The 2.6.5 futures exchange module is changed in one respect only: an
unresolved exchange is retried (see below); its identity rules, request fields,
spacing and order guard are unchanged.

## Changes

- **Ranking nodes.** KoreaStockRankingNode (LS t1441, t1452, t1463, t1444) and
  OverseasStockRankingNode (LS g3112) — see the [node reference](node_reference.md#rankingnode-순위-조회).
  The core classes raise an engine-version error from `execute()`, so an older
  engine that falls back to its generic executor (for example an unpinned
  install of programgarden 2.6.5, which would resolve core 2.6.3) reports an
  error instead of a silent `{"executed": true}` without rankings.
- **g3112 in the finance SDK**, and t1463 limited to the guide's 1 request per
  second.
- **Runtime values are data.** Expressions are evaluated only from templates
  authored in the workflow, at most once per node execution; CodeNode `code` is
  never evaluated — see the [expression guide](expression_guide.md).
- **LLM routing.** Gemini and DeepSeek credentials reach their own APIs — see
  the [AI agent guide](ai_agent_guide.md).
- **Futures exchange retry.** Only confirmed o3105 exchanges are remembered for
  a run. An unresolved contract is read again on a later account or
  pending-order node execution, at most once per 5 minutes per contract, still
  serialized and 2 seconds apart — see
  [futures position exchange](futures-position-exchange.md#rate-and-caching).
  In 2.6.5 an unresolved answer stayed `None` until the workflow restarted.

## Verification

Local Python 3.12 verification used a fresh virtual environment with the
candidate source packages installed in editable mode. The 2.6.5 comparison ran
the exported `28fa1f41` sources in the same environment (core, finance and
community are identical in 2.6.4 and 2.6.5).

| Suite | Candidate | 2.6.5 source |
|---|---|---|
| Engine | 3502 passed, 29 skipped, 3 xfailed, 5 failed | 3414 passed, 25 skipped, 3 xfailed, 5 failed |
| Core | 1618 passed, 1 failed | 1592 passed, 1 failed |
| Finance | 3287 passed, 10 failed | 3262 passed, 10 failed |
| Community | 1606 passed, 9 failed | 1606 passed, 9 failed |

The failures are the same cases on both sources (engine: three cancel-order
port assertions and two replay contract cases; core: the
OverseasStockHistoricalDataNode examples shape; finance: ten field-metadata
example cases; community: nine plugin cases). New cases: 49 ranking-node, 12
runtime-value, 16 g3112 SDK, 5 LLM routing and 5 futures exchange retry cases
(one 2.6.5 case that pinned the unresolved answer for the run was replaced;
four of the five fail on the 2.6.5 resolver), and 6 cases for the older-engine
ranking guard (4 core, 2 engine). Eleven of the twelve
runtime-value cases fail on the 2.6.5 source, as they did on 2.6.4; the
remaining one checks the unchanged NodeRunner behaviour. The other 2.6.5
futures exchange cases pass unchanged on the candidate. One futures order lifecycle
case built an auto-iteration config that its workflow never authored; it now
authors `order: "{{ item }}"` in the definition, and every lifecycle case
passes, including the 2.6.5 unresolved-exchange cases.

## Compatibility with older engines

Once core 2.6.3 and finance 2.0.3 are on PyPI, an unpinned install of an older
engine (programgarden ^2.6.x) resolves them. The full 2.6.5 engine suite run on
the candidate core and finance sources reports the same five failures as on
its own sources plus `test_every_registered_node_has_an_explicit_replay_boundary`,
which lists the registry and now sees the two ranking node types; 3423 cases
pass. Without the core guard the 2.6.5 engine ran a ranking node through its
generic executor and returned `{"executed": true}` without rankings; with the
guard it returns `KoreaStockRankingNode requires the programgarden engine 2.6.6
or later ...` and deep validation fails with `DEEP_VALIDATION_NODE_ERROR`.

Every node `_examples` workflow and the eight beginner guide samples were
deep-validated on the 2.6.5 source and on the candidate (no network): all 158
shared cases have identical validity, error codes and messages; the only
differences are the four new ranking examples and the ranking-based guide,
which 2.6.5 rejects as an unknown node type.

## Broker evidence

One read-only g3112 request was sent with a token that already existed in the
development token store (no issuance, no retry, a single HTTP request,
`natcode` US, `exgubun` 1, `rankgubun` 0): HTTP 200, `rsp_cd` 00000, 20 rows,
`tr_cont` Y, `cts_value` `0000000000000021`. `volume`, `amount`, `shareprc` and
`rec_count` arrived as JSON integers although the guide types them as String,
so the SDK models keep them as text. `keysymbol` was the exchange code plus the
symbol (`82AEHL`, `81AMTD`). The domestic ranking TRs were not called; their
request values come from the SDK examples and their responses were exercised
with the SDK models offline. No order, account change or LLM call was made.

## Publication

Finance 2.0.3 and core 2.6.3 were built twice from `41670a0e` with
`SOURCE_DATE_EPOCH` set to its commit time; both builds were byte-identical and
the archive members equal the package sources. Their dependency metadata equals
the published 2.0.2 and 2.6.2. They were uploaded to TestPyPI, installed in a
fresh environment from the verified TestPyPI wheels (other dependencies from
PyPI) together with the unchanged published engine 2.6.5, and passed 1551
offline cases with the network blocked (536 engine 2.6.5, 78 finance, 937
core), then uploaded to PyPI (finance first) and validated the same way from a
plain PyPI install. Published files:

| File | SHA-256 |
|---|---|
| `programgarden_finance-2.0.3-py3-none-any.whl` | `e964199a1b62f342739dd2f611dcdc25de7f1bdb98365b06cc817beab6aeddb3` |
| `programgarden_finance-2.0.3.tar.gz` | `d41bee9df0064c43d549747fca08bb29de496b6299deb84a19d00041138d9f17` |
| `programgarden_core-2.6.3-py3-none-any.whl` | `6c47fa605a82de97f9a083a7e690c94692a1acf58560a7590b985e8046cfed3c` |
| `programgarden_core-2.6.3.tar.gz` | `588fe84a7c1071a431193db921a417aa474b19c4e6df4b0f459fe478cbaa657f` |

The engine lock was then refreshed with Poetry 2.4.1 (`poetry lock`, no
upgrade): only the core and finance entries and the content hash change, and the
locked hashes are the published files above. The `src/core` and `src/finance`
trees of the merge commit equal those of `41670a0e`. The engine is built from
the merge commit and published after these packages.
