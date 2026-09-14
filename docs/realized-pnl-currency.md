# Realized PnL currency evidence

Owner request: show earned, lost and net money separately. The API already accepts
per-symbol realized outcomes, but cannot sum them without an explicit currency.

Implementation (Codex, engine 1.37.8, 2026-09-15):

1. Add nullable currency evidence to the local fill ledger without backfilling
   old rows or changing execution identity, FIFO amounts, ownership or counts.
2. Preserve COSAQ00102 CrcyCode only when every aggregated execution agrees.
3. AS1 has no currency. Use the matching broker position at fill time, requiring
   explicit symbol, market and currency fields. Keep fill recording before the
   existing account refresh. After refresh, annotate only that exact recorded
   execution; never create/replay a fill to attach currency.
4. A missing/mixed/conflicting unit remains unavailable. Futures FIFO amounts
   remain non-monetary regardless of currency. Fees are still excluded.
5. Verify old databases, exact replay, conflicts, zero/partial/closed positions,
   actual SDK fields, AS1 callbacks and downstream API aggregation offline.

Account-wide realized profit needs a broker TR/example that is not currently in
the SDK inventory. This change does not infer it from valuation PnL, deposits or
order amounts. Native packaging follows service and engine validation.

Validation: 246 focused tests pass on the host and against the installed wheel
in the Linux worker environment, with network blocked. The real engine envelope
also passes the existing API sanitizer and money projection: earned 10, lost 4,
net 6, separately in USD/HKD. Missing or contradictory currency projects null.
No new core, finance, community or HTTP contract is required.

The existing AS1 refresh still follows the durable fill write. Its failure cannot
erase the fill. A new position's currency is attached after refresh, and the next
ordinary PnL observation sees the changed ledger revision. Buffered pre-ACK fills
retain the annotation when their order arrives. No extra broker query is added.
Without usable execution identity, a later currency annotation is skipped.
Historical rows remain unknown; this release does not backfill old accounts.
