# CIDBQ02400 supplied LS field contract

Source: LS overseas futures order execution detail table and request/response
example supplied by the repository owner on 2026-09-09. This reference retains
published field metadata without copying account numbers, credentials, user IDs
or full account payloads from the example. Length/scale describes the published
wire format; this documentation does not add restrictive Pydantic validators.

## Request and continuation

Send `ThdayTpCode="0"` with `QrySrtDt`/`QryEndDt` in YYYYMMDD for historical
queries. Send `ThdayTpCode="1"` with **both date fields empty** for same-day
queries. The published field descriptions require this even though the example
combines same-day mode with nonempty dates. Logical collection time windows
remain separate from these transport fields.

For continuation, send `tr_cont="Y"` and the preceding response's
`tr_cont_key` while continuation is indicated. `tr_cont="N"` indicates no
continuation. Keep the request scope fixed across a cursor chain.

| Header field | Type | Required | Length | Published meaning |
| --- | --- | --- | --- | --- |
| content-type | String | Y | 100 | application/json; charset=utf-8 |
| authorization | String | Y | 1000 | OAuth access token; never log |
| tr_cd | String | Y | 10 | CIDBQ02400 |
| tr_cont | String | Y | 1 | Y: continuation; N: no continuation |
| tr_cont_key | String | Y | 18 | Previous continuation key |
| mac_address | String | Y | 12 | Required for corporate callers |

Response headers publish content-type, tr_cd, tr_cont and tr_cont_key with the
same types/lengths. All listed body fields are marked required in the supplied
table; response models retain their existing tolerant defaults.

| Input field | Type | Length | Published meaning |
| --- | --- | --- | --- |
| IsuCodeVal | String | 30 | Instrument code |
| QrySrtDt | String | 8 | Historical start YYYYMMDD; empty for same-day |
| QryEndDt | String | 8 | Historical end YYYYMMDD; empty for same-day |
| ThdayTpCode | String | 1 | 0: historical; 1: same-day |
| OrdStatCode | String | 1 | 0: all; 1: executed; 2: unexecuted |
| BnsTpCode | String | 1 | 0: all; 1: sell; 2: buy |
| QryTpCode | String | 1 | 1: reverse; 2: forward |
| OrdPtnCode | String | 2 | 00: all; 01: regular; 02: Average; 03: Spread |
| OvrsDrvtFnoTpCode | String | 1 | A: all; F: futures; O: options |

`RecCnt` appears in the supplied request example but is absent from the input
field table. This discrepancy does not establish a new required request field.
OutBlock1 echoes the input fields and adds RecCnt (Number, 5), AcntNo (String,
20), and Pwd (String, 8). Account/password echoes must not be logged.

## Execution evidence and published inconsistencies

`ExecDttm` is **execution datetime**, a 17-character timestamp; the existing
SDK format is YYYYMMDDHHMMSSsss. `OrdSndDttm` is order send datetime. Do not
substitute order placement/send time for execution time when counting a contest
interval. `OrdDt` and `OvrsFutsOrdNo` identify the dated broker order;
`OvrsFutsExecNo` identifies an execution, and `OvrsFutsOrgOrdNo` is a separate
original-order link. Multiple execution records for the same dated order do not
mean multiple orders. A never-executed cancellation contributes zero; canceling
the unexecuted remainder of a partially executed order leaves one executed order.

The output table says `FutsOrdStatCode` 0=all, 1=executed, 2=unexecuted. However,
its execution example returns **FutsOrdStatCode="4"**, TrdTpNm="체결",
TrxStatCodeNm="체결", positive ExecQty, OvrsFutsExecNo and ExecDttm. Preserve
this inconsistency. Do not exclude execution evidence solely because the output
code is not "1", or invent a universal meaning for "4". `OrdStatCode` is a
request filter and must not be confused with the response field.

`TrxStatCodeNm` lists "체결" and "체결취소". These are the supplied original
labels; the table does not explain how the latter links to an earlier execution
or changes its accounting. Keep the raw label. It is not sufficient evidence to
invent a reversal or treat an ordinary unfilled order cancellation as a trade.

The published media map is 00=branch, 22=iPhone, 23=Android, 41=API, 43=Robo API,
85=HTS, 96=final settlement, LP=loss cut, SK=CashCall and SO=conditional order.
The example uses **40**, which the table does not map. Preserve it as returned;
do not classify it by guessing a nearby code.

## OutBlock2 fields

All fields below are required according to the published table. Empty values in
the example remain possible. Numeric length/scale is transcribed, not a currency
unit or a statement that fee components are additive.

| Field | Type | Length/scale | Meaning or published values |
| --- | --- | --- | --- |
| OrdDt | String | 8 | Order date |
| OvrsFutsOrdNo | String | 10 | LS order number |
| OvrsFutsOrgOrdNo | String | 10 | Original LS order number |
| FcmOrdNo | String | 15 | FCM order number |
| ExecDt | String | 8 | Execution date |
| OvrsFutsExecNo | String | 10 | LS execution number |
| FcmAcntNo | String | 20 | FCM account number; sensitive |
| IsuCodeVal | String | 30 | Instrument code |
| IsuNm | String | 50 | Instrument name |
| AbrdFutsXrcPrc | Number | 30.11 | Exercise price |
| BnsTpCode | String | 1 | 0: all; 1: sell; 2: buy |
| BnsTpNm | String | 10 | Direction name |
| FutsOrdStatCode | String | 1 | 0: all; 1: executed; 2: unexecuted; example discrepancy above |
| TpCodeNm | String | 50 | 신규, 정정, 취소, 이관, 수관, 소멸, 장애 |
| FutsOrdTpCode | String | 1 | Table description blank; example has a value |
| TrdTpNm | String | 20 | 주문, 접수, 확인, 체결, 소멸, 거부 |
| AbrdFutsOrdPtnCode | String | 1 | Table description blank; do not infer a complete enum |
| OrdPtnNm | String | 40 | 시장가, 지정가, Stop Market, Stop Limit |
| OrdPtnTermTpCode | String | 2 | Table description blank |
| CmnCodeNm | String | 100 | 일반, Spread |
| AppSrtDt | String | 8 | Application start date |
| AppEndDt | String | 8 | Application end date |
| OrdQty | Number | 16 | Order quantity |
| OvrsDrvtOrdPrc | Number | 30.11 | Order price |
| OvrsDrvtExecIsuCode | String | 30 | Executed instrument code |
| ExecIsuNm | String | 50 | Executed instrument name |
| ExecBnsTpCode | String | 1 | Executed direction code |
| ExecBnsTpNm | String | 10 | Executed direction name |
| ExecQty | Number | 16 | Executed quantity |
| AbrdFutsExecPrc | Number | 30.11 | Execution price |
| OrdCndiPrc | Number | 30.11 | Order condition price |
| OvrsDrvtNowPrc | Number | 30.11 | Current price |
| UnercQty | Number | 16 | Unexecuted quantity |
| TrxStatCode | String | 2 | Processing status code; enum not supplied |
| TrxStatCodeNm | String | 40 | 체결, 체결취소; accounting effect not supplied |
| CsgnCmsn | Number | 19.2 | Consignment commission |
| FcmCmsn | Number | 21.4 | FCM commission |
| ThcoCmsn | Number | 19.2 | Company commission |
| MdaCode | String | 2 | Media code; map and example discrepancy above |
| MdaCodeNm | String | 40 | Media name |
| RegTmnlNo | String | 3 | Registered terminal number |
| RegUserId | String | 16 | Registered user ID; sensitive |
| OrdSndDttm | String | 17 | Order send datetime |
| ExecDttm | String | 17 | Execution datetime |
| EufOneCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| EufTwoCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| LchOneCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| LchTwoCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TrdOneCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TrdTwoCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TrdThreeCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| StrmOneCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| StrmTwoCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| StrmThreeCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TransOneCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TransTwoCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TransThreeCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| TransFourCmsnAmt | Number | 19.2 | Fee component; currency/additivity not supplied |
| OvrsOptXrcRsvTpCode | String | 1 | 1: exercise at expiry |
| OvrsDrvtOptTpCode | String | 1 | Overseas derivative option type |
| SprdBaseIsuYn | String | 1 | Spread base instrument flag |
| OvrsDrvtIsuCode2 | String | 30 | Second instrument code |

The supplied example returns HTTP-style response fields rsp_cd="00136" and
rsp_msg="조회가 완료되었습니다.". This is a published example, not a new
live test. It does not specify retained historical duration, currency per fee
field, or how to net lifecycle corrections; those facts are not invented here.

See [typed models](../programgarden_finance/ls/overseas_futureoption/accno/CIDBQ02400/blocks.py)
and [observed paper rejection responses](observed_broker_responses.md).
