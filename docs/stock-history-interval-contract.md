# Overseas-stock history interval contract

This local candidate fixes a reproduced mismatch in engine/core 2.6.0. The
registered `OverseasStockHistoricalDataNode` advertised intraday periods while
its executor sent LS `g3204` with the daily selector for every unknown interval.
For example, `interval: "1m"` produced a daily query and retained the requested
interval label. Synthetic request capture reproduced this without broker calls.

The supported periods are `1d`, `1w`, `1M` and `1Y`, mapped to the existing
`g3204` selectors `2`, `3`, `4` and `5`. The default remains `1d`. The fixed-only
authoring enum, Pydantic model, examples and English/Korean descriptions now
match those periods. Unsupported values fail static validation with
`INVALID_FIELD_ENUM` at the node's `interval` field and list the supported
values. The executor also rejects them with
`UNSUPPORTED_STOCK_HISTORY_INTERVAL` before credential access, login or a
synthetic deep-validation success. No automatic conversion is performed.

The finance SDK contains `g3203` and its matching example uses `ncnt=1`, but
that SDK capability is not connected to this registered workflow node. This
change does not add a g3203 node, raw `loctime`/`exevol`, response receipt time,
pagination completion or candle-finality evidence. Existing `value`/`values`
outputs retain date, OHLC and volume. Session inclusion, time-label semantics,
DST, corrections, missing bars, early closes, entitlement and actual quote delay
require an independently verified broker contract; no completion flag is
invented. A daily strategy is not a substitute for an intraday strategy.

Validation covers rejected periods before any credential/login access, exact
unchanged supported g3204 requests and outputs, public static-validation errors,
deep-validation bypass prevention, enum/localization consistency and existing
per-symbol iteration. Explicit legacy futures connections retain intraday support
in both normal and deep-validation paths. The 131 unique offline cases passed
(45 interval-contract cases and 86 existing regressions). All broker responses
are synthetic. The 2.6.1 release updates core and engine together. Finance and community are unchanged.
The engine dependency lock is refreshed after the new core distribution becomes
available, before final engine publication. Futures pagination changes remain a
separate candidate. No proprietary strategy examples are included.

Package publication and consumer adoption are separate release gates; source
validation does not establish that a deployed worker or tray has adopted this fix.
