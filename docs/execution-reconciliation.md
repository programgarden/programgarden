# Execution reconciliation foundation

Status: source-only P4 checkpoint, not a published runtime release.
Author: Codex, 2026-09-16.

## Runtime storage contract

`ProgramGarden.run`, `run_async`, executor execute/restore and checkpoint tools
accept an optional `execution_key`. It is a host-owned, globally unique identity
for the project and account execution, never an editable DSL field. The same
key resumes the same SQLite file after DSL/job ID changes. A different account
execution uses another file; old files are preserved. Legacy callers retain
their previous filename and behavior when the argument is absent.

Scoped positions, risk state and checkpoints share a filename derived only
from the SHA-256 hash of the key. The ledger binds the key, product, provider and
paper/live mode and rejects mismatches. Invalid keys fail before execution.
`database.execution_storage.prepare_execution_storage` now provides host adoption.
The authenticated server must supply exactly one project account-execution ID.
It copies a matching legacy database with SQLite backup (including committed WAL),
leaving the original file and P3 marker untouched. The marker must positively bind
the project and execution; unknown/mixed ownership or multiple candidates holds
startup. Existing ledger rows must match product, provider and paper/live mode
before the engine binds the copied database. A changed DSL ID does not reset state.

Project and execution file locks remain held until engine shutdown completes.
Account switches cannot overlap an old writer. The target is published atomically
and never overwrites an existing file. Windows uses byte-range file locking;
Windows packaging and runtime verification remain owner-managed. Locks coordinate
writers sharing a storage directory; server execution ownership still controls
cloud-versus-desktop starts. Worker/tray source wiring is implemented and tested,
but not published. Do not enable a deployed host before the remaining P4 gates.

## Verified adjustment boundary

The scoped BrokerNode reads complete, fresh broker holdings and pending-order
evidence before strategy execution. Missing raw blocks, rejected queries,
continuation, dropped parser rows, missing quantities, wrong query scope and
ambiguous identities hold startup. A changed fill revision also invalidates the
snapshot. Broker calls in the tests are intercepted; no real orders are sent.

Only a reduction of existing workflow-owned lots is allowed. Broker excess is
never imported. The FIFO reduction and its basis audit commit together; failure
rolls both back. No synthetic trade_history row, realized profit, win or fill
notification is created. An actual adjustment emits `position_reconciled` via
the existing risk-event listener; no change emits no event. SQLite adjustment
history is implemented, but cloud persistence and the user-facing history are
still pending.

Scoped manual/other fills consume only non-workflow lots. This prevents a late
manual sell from applying an already observed startup reduction twice. External
changes to owned lots require a new verified reconciliation. Legacy behavior
remains unchanged. Scoped cancellation notifications retain order ownership so
a late partial fill cannot lose attribution; final cancellation reconciliation
is not yet implemented.

## Approved order-total recovery (2026-09-16)

A missed sell is recovered before trimming. The owner approved recovery from
broker-confirmed order totals, estimated PnL and exclusion from individual-fill
and win-rate statistics. Unknown totals continue to hold startup.

The owner reports that no historical overseas-stock individual execution-number
TR could be found. COSAQ00102 supplies order-level quantities and average prices;
AS1 supplies individual execution identity live. Do not invent a historical
execution number or treat an order total as a new individual fill.

`database/order_recovery.py` implements atomic recovery for original orders that
are fully filled with no remaining quantity. It subtracts already retained fills,
requires exact execution/account scope, date, symbol, side, quantity and currency,
and stores separate `workflow_order_recoveries` provenance. It never inserts an
invented `trade_history` row or execution ID. Legacy unidentified rows retain
their original contents and receive separate aggregate provenance.

Late identified executions consume persistent coverage, without a second FIFO
mutation, trade outcome or fill notification. Conflicting quantity/price/date
evidence is rejected. A buy whose earlier basis would require rewriting an
already-valued sale remains held. A recovered cost basis makes subsequent related
realized money estimated, excluded from outcome counts. Recovery money is also
excluded from the measured profit/loss ratio numerator and denominator.

`broker_order_totals.py` uses the SDK history request with exact dates and bounded,
spaced queries. Live read-only evidence on 2026-09-16 confirmed two fully filled
original orders. It also exposed `tr_cd=COSAQ` and single-digit BnsTpCode values
(`1` sell, `2` buy). The strict reader now recognizes only specifically observed
short headers and still requires full TR-specific blocks, terminal continuation
and matching query echoes. No arbitrary prefix matching is allowed. Captured
responses were replayed through the real SDK parser and recovery adapter without
further broker requests or ledger writes. No trade was submitted.

Partially filled/cancelled orders, amendment chains, pagination and ambiguous
legacy dates remain held. Absence from pending orders does not prove cancellation.
The owner could not obtain authoritative COSAQ00102 enum/quantity mappings and
suggested live observation. Three additional read-only history requests found
four old unfilled cancellation pairs (history date 2026-08-19). Normal and cancel
rows both explicitly returned MrcTpCode="" and OrdTrxPtnCode=0; the names differed.
Cancellation children had CnfQty=1 and their originals had CnfQty=0. Fully filled
originals still had OrdTrxPtnNm="접수완료". Neither codes nor display names alone
establish execution state. SDK field descriptions retain these limited observed
facts instead of unobserved enum examples. Partial-fill/amendment semantics remain
unverified; no recovery eligibility changed. A manual pending order also blocks
a reduction of that instrument.

Personal evidence becomes `version:3` only when recovery exists. Groups add
`recovery_excluded_quantity`, `recovery_gross_profit`, `recovery_gross_loss`; the
estimated basis is `fifo_with_order_total_recovery`. `order_recovery` carries a
count, `is_estimated:true`, `basis:broker_order_total` and
`excluded_from_trade_count:true`. Closed-trade status is partial, with reason
`aggregate_recovery_excluded`. Server and dashboard must support this envelope
before a runtime is enabled; v1/v2 behavior remains compatible.

## Remaining integration gates

- Obtain missing partial-cancel/modify evidence; the recovery policy is approved.
- Exercise the implemented worker/tray storage adoption on stopped dev fixtures
  before runtime publication; unknown legacy ownership still requires review.
- Complete explicitly owned pending cancellation; distinguish submission from
  confirmed outcome. Emergency market liquidation remains excluded.
- Persist and render the adjustment history with brief localized notifications.
- Review recovery/subscription ordering and late-event races end to end.
- Keep futures short-position accounting distinct from the existing buy-lot FIFO;
  the current adapter must not net shorts into available long quantity.
- Run integrated dev verification before PyPI and runtime pin updates; native
  builds remain last. This checkpoint changes no published version or live job.

## Validation

The foundation passed 333 focused tests: scoped SQLite storage, rollback and identity, missing and
partial sells, late external fills, SDK response contracts, startup notification,
checkpoint, execution deduplication, broker shutdown and futures order lifecycle.
The expanded run exposed nine pre-existing lifecycle fixture failures at clean
baseline `d62dc5c`; the same failures reproduced in an isolated worktree. Fixtures
now include the current futures balance hook and domestic/futures snapshot methods.
The recovery follow-through passes 252 focused engine tests, including real SDK
parser boundaries, startup sequencing, legacy provenance, covered live replay,
same-number adjacent dates and accounting. Five real SQLite-produced evidence
fixtures pass the server and dashboard contract readers. The API has 112 passing
tests; the dashboard has 47 focused invariants, clean type/lint checks and four
actual-component browser cases (KO/EN, 390/1280 widths, popovers and Escape).
The first three read-only history probes were made: the first exposed a local probe's use
of a nonexistent diagnostics attribute, and the next two captured the short-header
contract. Subsequent verification replayed captured responses offline. No
production ledger mutation, cancellation, new trade or workflow restart was performed.
The later lifecycle diagnostic made three more history queries; its bounded
collector has 20 offline tests in the server repository. Captures preserve raw
field presence and private order links. No partial-fill cancellation was observed;
a separate owner-executed test awaits owner-selected order terms.


## Host adoption checkpoint (2026-09-16)

The worker holds managed storage until its sole awaited engine shutdown completes;
failed cleanup keeps the OS lease until child exit. Desktop validation uses an
isolated temporary directory and never rewrites live markers. Desktop stop requests
cancel the runner once; its finally block owns the only checkpoint writer. A
failed/unfinished shutdown holds the next start before a new bridge is opened.
This checkpoint changes no package versions or running user workflows.
