# Observed LS broker responses

## COSAQ00102 real overseas-stock empty responses (2026-09-09)

Two read-only observations at 13:32:35 and 13:32:37 UTC returned HTTP 200,
`rsp_cd="02679"` and the exact message `조회내역이 없습니다.`. Both contained
`COSAQ00102OutBlock1` and `COSAQ00102OutBlock2`, an explicitly present empty
`COSAQ00102OutBlock3` list, `tr_cont="N"` and no continuation key. Requests used
`OrdDt="20260909"`, `ThdayBnsAppYn="1"`, `ExecYn="0"`, `SrtOrdNo=999999999`,
and separate `OrdMktCode="81"` and `"82"` values. No order was submitted.

These observations establish only those response envelopes and request scopes.
A subsequent read at 14:04:38 UTC used the tracker's exact pending query:
`OrdMktCode="00"`, `ExecYn="2"`, `OrdDt="20260909"`, `ThdayBnsAppYn="1"`,
`SrtOrdNo=999999999`. It returned HTTP 200, the same code/message, explicit
echo/aggregate/empty detail blocks, `tr_cont="N"` and no continuation key.
The response echoed `OrdMktCode="%"`, the requested date and current-day flag,
`BnsTpCode="0"` and `CrcyCode="000"`.

The tracker accepts this observed no-data envelope only with those matching
echoes and terminal continuation metadata. It replaces the pending cache for
its existing query and clears the prior error. Missing blocks, mismatched
scope/date, nonempty 02679 responses and continuation pages retain the cache.
The code is not added to generic success codes. This does not establish
every-market coverage or complete historical execution counts.
Additional explicitly returned query fields must agree with the request. A
detail object, string or null is a malformed response, not an empty array.

## FOCCQ33600: periodic report with an overseas-stock credential

The existing `example/korea_stock/run_FOCCQ33600.py` demonstrates a dated
account periodic-return request. A read-only request at 14:15:04 UTC on
2026-09-09 used the existing real overseas-stock credential's shared token,
the SDK's `/stock/accno` route, `QrySrtDt="20260901"`,
`QryEndDt="20260909"` and `TermTp="1"`. The broker returned HTTP 200,
`rsp_cd="00136"`, `rsp_msg="조회가 완료되었습니다."`, terminal continuation,
the matching query echo, an account summary and eight daily rows dated
September 1 through 8. September 9 was absent from this response.

The returned fields include `InvstPlAmt`, `InvstErnrat`, `MnyinAmt`,
`MnyoutAmt`, and daily opening/closing valuations and `TermErnrat`. The field
contract labels monetary amounts as KRW. This successful response does not
make the report a USD-only stock PnL series, establish a live current-day
sample, or prove the inclusion rules for every asset type. Keep the requested
period, actual returned dates, reporting currency and broker source explicit.
Do not infer support from the example's directory name alone.

The separate `example/korea_stock/run_CDPCQ04700.py` demonstrates transaction
history with commission and tax fields. Its existence is not evidence that
all those fields have been live-tested for overseas stocks.

A separate confirmed structural defect is fixed: an omitted OutBlock3 must not
count as an explicitly empty detail block. COSAQ00102 keeps its public `block3`
default of `[]`, while `model_fields_set` retains whether the detail block was
present. StockAccountTracker requires that presence before its existing empty
00000 response path can clear pending orders. Missing/error/unknown-code
responses preserve the previous cache and their original diagnostics. This
presence guard does not establish market coverage or continuation completeness.

This reference records directly observed responses, scoped to their TR and
account mode. It is not a universal response-code dictionary. Preserve the
original `rsp_cd` and `rsp_msg`; do not infer an undocumented rejection cause
from the code or substitute another broker's message table.

## CIDBT00100: overseas futures paper order rejection

Observed on 2026-09-09 at 11:11:28 KST (UTC+09:00) through the normal
chat-generated workflow and local desktop runner.

| Field | Observed value |
| --- | --- |
| Account mode | Overseas futures PAPER |
| TR | `CIDBT00100` (new order) |
| Instrument | `CUSU26`, HKEX |
| Request | BUY, 1 contract, LIMIT 6.7043 |
| HTTP status | `200` |
| `rsp_cd` | `01425` |
| Original broker message | `모의투자 주문가능금액이 부족합니다.` |
| Order identifier | Not returned |
| Outcome | Rejected; no accepted order or new fill confirmed |

The original message means the paper orderable amount is insufficient. This
observation does not establish the account's currency balances, margin rules,
funding requirements, or the meaning of this code in another TR/account mode.

The normal failed-order journal preserved the exact message in
`order_fills.diagnostics.raw_msg` and
`raw_event.engine_result.diagnostics.raw_msg`. The engine's `error` field
retained `Empty OrderNo: 모의투자 주문가능금액이 부족합니다.`.
The `Empty OrderNo:` prefix is added by the engine, not by the broker.
The failed record was timestamped `2026-09-09T02:11:28.551292Z`.
A separate task observer captured only the response code; a read-only journal
inspection recovered the message without issuing another broker request.
Missing observer output does not mean the broker omitted `rsp_msg`.

HTTP 200 alone does not establish order acceptance. A failed journal record is
also not an executed trade. Keep acceptance, positive execution and workflow
terminal status separate when reporting the result.

## CIDBQ01400: subsequent paper orderable-quantity reads

On the same paper account, read-only requests returned HTTP 200,
`rsp_cd=00136`, and `rsp_msg=모의투자 조회가 완료되었습니다.`.
Both responses explicitly contained `CIDBQ01400OutBlock2.OrdAbleQty`.

Shared request fields: `RecCnt=1`, `QryTpCode="1"` (new order),
`BnsTpCode="2"` (buy), and `AbrdFutsOrdPtnCode="2"` (limit).

| Observed at (KST, 2026-09-09) | `IsuCodeVal` | `OvrsDrvtOrdPrc` | `OrdAbleQty` |
| --- | --- | --- | --- |
| 11:26:50 | `CUSU26` | 6.7043 | 0 |
| 11:26:56 | `HMHU26` | 25260.0 | 44 |

The HMHU26 price came from an actual `o3105` response identifying HKEX
`Mini Hang Seng(2026.09)`, with `TrdP=25260.0`,
`KorDate=20260909`, and `RcvTm=112652`. It was a last-trade price,
not a confirmed current ask. The quantity is specific to that account, time,
instrument, side and limit price; it is not a fill guarantee or a default for
other users. No order was placed by these quantity queries.

See the typed request/response fields in
[`CIDBQ01400/blocks.py`](../programgarden_finance/ls/overseas_futureoption/accno/CIDBQ01400/blocks.py).
These observations do not introduce automatic order retries or change SDK
success-code classification. Missing output blocks/quantity remain unknown;
do not replace them with a successful zero result.

## HMHU26: accepted paper order, later execution and holding

On 2026-09-09, a normal chat-generated workflow was validated, saved and run
through the local desktop UI. It submitted one HMHU26/HKEX PAPER BUY order for
one contract at LIMIT 25250. No retry or cancellation was submitted.

| Event (KST) | Observed evidence |
| --- | --- |
| 12:09:15.501, order response | `CIDBT00100`, HTTP 200, `rsp_cd=00040`, original `rsp_msg=모의투자 매수주문이 완료 되었습니다.`, order ID present |
| 12:09:17 and 12:09:27, order reads | `CIDBQ01800`, `ExecQty=0`, `UnercQty=1` |
| 12:09:32.213, actual execution time | `CIDBQ02400.ExecDttm=20260909120932213`, `ExecQty=1`, `AbrdFutsExecPrc=25247`, `UnercQty=0`, execution ID present |
| 12:09:37.913, execution-detail response | HTTP 200, `rsp_cd=00136`, one row, terminal continuation |
| 12:09:39.234, holdings response | `CIDBQ01500`, HTTP 200, `rsp_cd=00136`, positive HMHU26 holding |

The execution-detail request used `ThdayTpCode="1"` with both query dates
empty. Its raw row contained `OrdDt=20260909`, `ExecDt=20260909`,
`ExecBnsTpCode="2"`, `OvrsDrvtExecIsuCode="HMHU26"`,
`FutsOrdStatCode="1"`, `TpCodeNm=""`, and `TrdTpNm="매수"`.
The positive execution quantity, execution ID and actual execution timestamp
were matched to this submitted order privately. Account and order identifiers
are intentionally absent from this reference.

The contemporaneous `CIDBQ01800` row retained `FutsOrdStatCode="3"` and
`TpCodeNm="확인"` even after its `ExecQty` became 1. Preserve these TR-specific
observations without inventing a shared status-code mapping. The
[`CIDBQ02400 contract reference`](cidbq02400_contract.md) also retains the
official table/example discrepancy; this one observed row does not erase it.

The user independently confirmed the holding in the Toohon overseas-futures
paper account. The finite workflow had already completed at 12:09:24, before
the actual execution. Its pre-fill order journal and PnL flush therefore do
not, by themselves, prove post-fill journal ingestion, account return, MDD or
contest ranking persistence. Those require separate evidence.

## CIDBQ02400: response transaction-code mismatch during paper recovery

At 15:05:25 KST on 2026-09-09, the normal desktop recovery worker requested
`CIDBQ02400` on the overseas-futures PAPER account. The SDK response passed
HTTP 200 / `rsp_cd=00136` / no SDK error and retained the original message
`모의투자 조회가 완료되었습니다.`. Its parsed response header contained
`tr_cd="CIDBQ"`, while the request header contained `tr_cd="CIDBQ02400"`.

The bounded desktop history adapter rejected this response with its own
`unexpected_response_tr` error before retaining that page's execution facts.
This is an application validation failure, not a broker order rejection or
proof that the previously confirmed HMH execution disappeared. The canonical
SDK response model does not change the header value. The meaning and accepted
scope of the shortened response code have been referred to the user for
confirmation; no alias mapping or response-code inference has been added.

A separate offline fixture exposed case-sensitive HTTP header-name validation.
That fixture is not the observed cause of this transaction-code value mismatch.

The desktop adapter was subsequently changed to validate the exact authenticated
HTTPS request, named response blocks and all nine echoed query fields. The
supplied response-header contract and SDK do not impose the adapter's former
request/response value-equality condition. This change retains the raw header
without defining an LS alias; missing or mismatched query echoes still reject
the page, and historical coverage remains unverified.

At 16:38:02 KST the normal desktop recovery worker retained the original HMHU26
execution through this path. Its normal server-backed monitoring view showed
one execution, quantity1, price25247 and execution time12:09:32.213. A second
automatic poll at16:39:09 retained one observation, with one acknowledged server
delivery and no duplicate execution. No new order was submitted. The original
pre-fill parent remains immutable; the displayed filled state comes from its
separate execution observation and remains explicitly unverified local
telemetry. This proves post-workflow recovery, not account return/MDD or complete
contest history. Raw headers from these two successful polls were not archived,
so this result does not assert their exact response `tr_cd` value.


## CSPAQ13700: incomplete domestic-stock history observation

A read-only real-account probe on2026-09-09 at approximately00:43 UTC recorded
HTTP200, `rsp_cd="01001"`, `tr_cont="N"` and no saved output blocks. The probe
artifact omitted `rsp_msg`; its original text cannot be recovered from that
artifact. No meaning for01001, empty-history success, account permission or
request rejection is established by this record.

The request used all-market/both-side/all-symbol/filled-and-unfilled filters,
an explicit current KST date and starting order number999999999. Its manually
constructed body omitted `OrdPtnCode`. This is a request-shape observation,
not an established cause of the response. A future diagnostic must preserve
the original code and message without exposing account fields.

The local typed contract describes CSPAQ13700 as order/execution history,
including per-order cumulative quantities and average execution prices.
CSPAQ00600 describes credit/margin limits and orderable amounts, not execution
history. The README shorthand has been corrected to match these model
contracts. A dated order number does not supply the calendar execution date,
individual partial-fill ledger or complete historical coverage.
