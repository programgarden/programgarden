# Native futures details and durable strategy state

Version 2.6.0 adds OverseasFuturesContractInfoNode. It reads one
explicit `{symbol, exchange}` with o3105 through the selected futures broker
connection. It does not require a positive quote or submit an order. Live,
identity-only deep validation, and recorded raw-response replay share the same
projection in `programgarden/futures_contract_info.py`.

`value` contains observed dates in YYYY-MM-DD, reported local/Korean session
times, currency, margins and tick values. `verified=true` means a successful
response matched symbol/exchange, not that every optional field is available.
Absent/invalid optional fields remain null and appear in `missing_fields`.
`error` contains a safe diagnostic on failure. Margin units, status-code enums,
session offsets, expiry dates and missing numeric values are not inferred.

The node reads exactly one identity even when its predecessor exposes an array.
An explicit SplitNode can bind `nodes.split.item` for a batch. Resolve a listed
successor with FuturesContractNode and inspect the actual held contract's expiry.
Neither this metadata nor an order acknowledgement establishes a confirmed fill.

SQLiteNode adds `storage_scope=execution`; `shared` remains the default. Execution
scope creates a stable hashed filename under the existing host-injected
`storage_dir`, using execution_key or a standalone workflow_id. job_id is not
part of the key. Restarting with the same identity/root retains state; a separate
execution uses a different file. Existing shared databases are not migrated or
deleted. Offline replay uses the same naming rule below its disposable root.
Persistence depends on the host supplying durable storage, not the node alone.

SessionGateNode accepts XHKG and respects scheduled lunch breaks, holidays and
half-days from the pinned exchange-calendars package. This is a cash-market
calendar, not complete futures-session or live-halt evidence. A strategy must
state its calendar policy and separately require applicable broker session data.

The futures order-event node now declares its existing TC3 order_date, fill_no,
fill_time, svc_id and tr_cd fields. It selects the exact futures credential and
refuses reuse of an existing event stream from a different broker connection.
Missing fills after a disconnect still require reconciliation; this change does
not invent recovery events or authorize retries of ambiguous orders.

Focused validation includes SDK field contracts, absent/invalid metadata,
credential isolation, raw replay, durable SQLite reopen/isolation, existing stock
event streams and XHKG calendar boundaries. The AI repository separately tests
the unchanged rollover examples with native CodeNode/SQLite and recorded broker
boundaries, including partial/duplicate/conflicting fills and restart states.
