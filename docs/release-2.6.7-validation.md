# Version 2.6.7 release validation

Engine 2.6.7 and programgarden-finance 2.0.5 are released together on
2026-10-16. Core 2.6.3 and community 2.3.1 are unchanged. The engine now
requires finance ^2.0.5. The base is main `edb66a49` (engine 2.6.6, finance
2.0.4; finance 2.0.4 is the separate domestic open-orders fix from PR #114).

## Changes

- **Futures TC2 is readable (finance 2.0.5).** LS sends `user_id` where the
  guide says `userid`, and a blank `ordr_typ_cd` on cancel confirmations. Both
  failed validation, so every TC2 listener received `body=None` since TC2 was
  added. Evidence: LS paper overseas futures, 2026-10-15
  (`src/finance/tests/fixtures/tc_frames_paper_futures_20261015.json`, ids
  replaced).
- **Engine TC2 handling (2.6.7).** A futures modify and a cancel each get their
  own new order number (`ordr_no`); the modified or cancelled order is in
  `orgn_ordr_no`. The engine now finds the workflow's order through
  `orgn_ordr_no`, reads the guide's side codes (`"1"` sell, `"2"` buy), never
  invents an order date from the local clock, and changes nothing when the side
  or symbol does not match the ledger row. A cancel confirmation cancels the
  owned original order; a modify confirmation updates the successor row recorded
  by ModifyOrderNodeExecutor; a modify made outside the workflow is logged only.
  RealOrderEventNode (futures) skips a frame the SDK could not read instead of
  emitting an empty `accepted` event.
- **Account events after a reconnect (finance 2.0.5).** Real-time clients
  register account (order event) TRs again after a reconnect, following the
  market-data resubscription (`reregister_account_events_on_reconnect`, default
  on). LS paper showed that a new socket gets no account events until it
  registers again.
- **Futures account unregister (finance 2.0.5).** Overseas futures `Real` sends
  one account unregister when its last listener leaves and registers again for
  a later listener. Other sockets on the same token keep their events.
- **Other finance 2.0.5 items.** Header-only continuation for six account TRs
  (`occurs_req`), `SetupOptions.transient_retries`, FuturesAccountTracker open
  orders keyed by the integer order number with the CIDBQ01800 field names,
  TC1 `xrc_rsv_tp_code`, COSAT00400 at 1 request per second, COSAT00301
  rejecting a buy with sell-only price types, and reconnect detection that does
  not depend on the backoff value. See `src/finance/CHANGELOG.md`.

## What changes for running workflows

Finance 2.0.5 makes listeners that were inert start acting:

- futures TC2 HO02 confirmations reach the engine's fill ledger and the futures
  account tracker (one debounced refresh per confirmation, the same three reads
  as after a fill);
- futures RealOrderEventNode TC2 frames reach the `modified`, `cancelled` and
  `rejected` outputs with data;
- reconnected sockets register account events again; a futures `Real` without
  listeners unregisters them.

Engine 2.6.6 requires finance ^2.0.3, so an unpinned install of 2.6.6 also
resolves finance 2.0.5 and would run the 2.6.6 TC2 handler (`ordr_no`, inverted
side codes) on readable frames. Publish both together and pin both versions in
every consumer. First-party consumers pin finance exactly (2.0.2 or 2.0.4 at
the time of release), so they keep the old SDK until their pins move.

## Verification

Local Python 3.12, two fresh virtual environments with the same third-party
packages (pytest 8.4.2, pytest-asyncio 0.21.2) and the four source packages
installed in editable mode: one from this tree, one from `edb66a49`. Each
package suite ran from its own directory.

| Suite | 2.6.7 / finance 2.0.5 | `edb66a49` (2.6.6 / finance 2.0.4) |
|---|---|---|
| Engine | 3529 passed, 29 skipped, 3 xfailed, 5 failed | 3504 passed, 29 skipped, 3 xfailed, 5 failed |
| Finance | 3442 passed, 10 failed | 3303 passed, 10 failed |
| Core | 1618 passed, 1 failed | 1618 passed, 1 failed |
| Community | 1606 passed, 9 failed | 1606 passed, 9 failed |

The failing cases are identical on both trees (engine: three cancel-order port
assertions and two replay cases; finance: ten field-metadata example cases;
core: one; community: nine). New cases: 25 engine TC2 confirmation cases that
replay the captured frames, and 139 finance cases (TC2/TC1 frames, account
re-registration, futures unregister, continuation, transient retries, overseas
stock order contracts, guide rates).

Engine 2.6.6 (`edb66a49`) run against the finance 2.0.5 source: 3504 passed,
29 skipped, 3 xfailed and the same 5 failures. Its suite has no TC2
confirmation cases, so this shows only that 2.6.6 still imports and runs on
finance 2.0.5, not that its TC2 handling is correct.

## Packaging

Finance 2.0.5 and engine 2.6.7 were built from an export of this tree with
Poetry 2.4.1 and `SOURCE_DATE_EPOCH` set to the release-prep commit time. The
dependency metadata equals the published finance 2.0.4 and engine 2.6.6 except
the engine's finance lower bound (`>=2.0.5`). A fresh environment installed the
two wheels with core 2.6.3 and community 2.3.1 from PyPI (`uv pip check`
clean) and passed the engine TC2 confirmation cases (25) and the new finance
cases (139) from copies of the test directories.

## Publication

Both packages were built from an export of the engine branch with
`SOURCE_DATE_EPOCH=1792085033` (the release-prep commit time); a second build
from the following commit was byte-identical. The `src/finance` tree of the
#112 merge commit `3ab277ec` (tag `finance-v2.0.5`) equals the built tree.
Finance 2.0.5 was uploaded to PyPI first (17:30:52Z) and engine 2.6.7 five
seconds later (17:30:57Z). Published files:

| File | SHA-256 |
|---|---|
| `programgarden_finance-2.0.5-py3-none-any.whl` | `7ff15b2910cfd46bba42e4df24b9bdae502152d7316e18c27913e2e1d2b1a1d1` |
| `programgarden_finance-2.0.5.tar.gz` | `f5317c32d85d2eef7e79a07d7a681798d7313eb3e27b004d04e7321e6e76414b` |
| `programgarden-2.6.7-py3-none-any.whl` | `859bafc29b1ed10c0c36afac19c55fcf6edc4f11d79c1f420a0d2fa246ff9876` |
| `programgarden-2.6.7.tar.gz` | `5b224bfe686a2609e94b8af8b02077574e725fe4f46648a6f826d37784b360a0` |

A fresh environment installed `programgarden==2.6.7` from PyPI, resolved
finance 2.0.5, core 2.6.3 and community 2.3.1 (`uv pip check` clean) and
passed the 25 TC2 confirmation and 139 new finance cases. The engine lock was
then refreshed with Poetry 2.4.1 (`poetry lock`, no upgrade): only the finance
entry and the content hash change, and the locked hashes are the published
files above.
