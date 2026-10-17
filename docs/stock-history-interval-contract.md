# Overseas-stock history interval contract

## 2.7.0: minute bars through LS g3203

Engine/core 2.7.0 connect LS `g3203` (해외주식 차트 N분) to
`OverseasStockHistoricalDataNode`. Supported intervals:

| Interval | TR | Selector |
| --- | --- | --- |
| `1d`, `1w`, `1M`, `1Y` | g3204 | `gubun` 2, 3, 4, 5 |
| `1m`, `5m`, `10m`, `15m`, `30m`, `60m` | g3203 | `ncnt` 1, 5, 10, 15, 30, 60 |

Each `ncnt` was checked with one live read-only call (platform overseas-stock
key, a stored unexpired token, no token issuance, NVDA, 2026-10-18 01:34 and
01:52 KST, US market closed): HTTP 200, `rsp_cd=00000` 「조회완료」,
`tr_cont=Y`, 40 rows ascending with exactly that step (30 and 60 also show the
gap between sessions), parsed by the finance `G3203OutBlock`/`G3203OutBlock1`
models. LS has no overseas-stock paper trading, so there is no paper variant.

What a minute read returns:

- one page (`qrycnt=500`, the LS cap for an uncompressed page): the newest up
  to 500 bars at or before `end_date` within `start_date..end_date`. The
  continuation cursor (`cts_date`/`cts_time`) is not followed, so a long range
  is not complete;
- `date` = `YYYYMMDD` + `loctime` (`YYYYMMDDHHMMSS`), the exchange local time
  label exactly as LS returns it (whether it marks the bar's start or end was
  not established), `volume` = `exevol`, rows sorted oldest first;
- pre-market and after-hours bars as LS returns them (observed: 15-minute bars
  08:15–18:00 and 60-minute bars from 02:00 local time). Filter by the time part
  of `date` when a strategy needs the regular session only;
- no completion or finality flag: the newest bar may still be forming;
- a g3203 error or a parse failure is an empty series with a warning, never a
  daily series.

Other values (`1h`, `1min`, `2m`, `30s`, ...) are still refused by the schema,
static validation (`INVALID_FIELD_ENUM`) and the executor
(`UNSUPPORTED_STOCK_HISTORY_INTERVAL`) before credentials or login. Deep
validation fixtures for minute intervals carry `YYYYMMDDHHMMSS` stamps.

## 2.6.1: periods only (history)

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
