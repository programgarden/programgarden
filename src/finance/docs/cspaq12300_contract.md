# CSPAQ12300 owner-confirmed source contract

Source: LS OpenAPI table and example supplied by the owner on2026-09-15.
The owner explicitly confirms that **every OutBlock2 field is not provided**.
A read-only response contained zero/empty placeholders while CSPAQ22200 returned
nonzero cash. Field presence does not turn these placeholders into evidence.
Each summary field therefore has a visible description and ls_availability
schema metadata; response.block2_status remains not_provided.

## Request

POST /stock/accno; one request/second per shared app key. Keep rate limits.
BalCreTp:0 all,1 cash equity,9 futures substitute collateral.
CmsnAppTpCode:0 exclude valuation commission,1 include.
D2balBaseQryTp:0 all rows,1 D+2 quantity at least zero.
UprcTpCode:0 average price,1 BEP. All four have source length1.
The official example also sends RecCnt=1 although its input table omits it.
The SDK retains this example field and documents the discrepancy.

## Entire unavailable summary block

The table marks these fields required; the live-availability instruction
supersedes that notation for accounting use. Legacy EvalPnl is retained and
marked deprecated; the supplied summary field is EvalPnlSum. Neither can be
used as actual account PnL. No alias between them is invented.

| Field | SDK type | Source label (English) | Source length |
| --- | --- | --- | --- |
| RecCnt | int | Record count | 5 |
| BrnNm | str | Branch name | 40 |
| AcntNm | str | Account name | 40 |
| MnyOrdAbleAmt | int | Cash orderable amount | 16 |
| MnyoutAbleAmt | int | Withdrawable amount | 16 |
| SeOrdAbleAmt | int | Exchange orderable amount | 16 |
| KdqOrdAbleAmt | int | KOSDAQ orderable amount | 16 |
| HtsOrdAbleAmt | int | HTS orderable amount | 16 |
| MgnRat100pctOrdAbleAmt | int | 100 percent margin orderable amount | 16 |
| BalEvalAmt | int | Balance valuation | 16 |
| PchsAmt | int | Purchase amount | 16 |
| RcvblAmt | int | Receivable amount | 16 |
| PnlRat | float | Profit and loss ratio | 18.6 |
| InvstOrgAmt | int | Investment principal | 20 |
| InvstPlAmt | int | Investment profit and loss | 16 |
| CrdtPldgOrdAmt | int | Credit collateral order amount | 16 |
| Dps | int | Cash deposit | 16 |
| D1Dps | int | D+1 cash deposit | 16 |
| D2Dps | int | D+2 cash deposit | 16 |
| OrdDt | str | Order date | 8 |
| MnyMgn | int | Cash margin | 16 |
| SubstMgn | int | Substitute margin | 16 |
| SubstAmt | int | Substitute amount | 16 |
| PrdayBuyExecAmt | int | Previous-day buy execution amount | 16 |
| PrdaySellExecAmt | int | Previous-day sell execution amount | 16 |
| CrdayBuyExecAmt | int | Current-day buy execution amount | 16 |
| CrdaySellExecAmt | int | Current-day sell execution amount | 16 |
| EvalPnlSum | int | Total valuation profit and loss | 15 |
| DpsastTotamt | int | Total deposited assets | 16 |
| Evrprc | int | Expenses | 19 |
| RuseAmt | int | Reusable amount | 16 |
| EtclndAmt | int | Other loan amount | 16 |
| PrcAdjstAmt | int | Provisional settlement amount | 16 |
| D1CmsnAmt | int | D+1 commission | 16 |
| D2CmsnAmt | int | D+2 commission | 16 |
| D1EvrTax | int | D+1 taxes | 16 |
| D2EvrTax | int | D+2 taxes | 16 |
| D1SettPrergAmt | int | D+1 scheduled settlement | 16 |
| D2SettPrergAmt | int | D+2 scheduled settlement | 16 |
| PrdayKseMnyMgn | int | Previous-day KSE cash margin | 16 |
| PrdayKseSubstMgn | int | Previous-day KSE substitute margin | 16 |
| PrdayKseCrdtMnyMgn | int | Previous-day KSE credit cash margin | 16 |
| PrdayKseCrdtSubstMgn | int | Previous-day KSE credit substitute margin | 16 |
| CrdayKseMnyMgn | int | Current-day KSE cash margin | 16 |
| CrdayKseSubstMgn | int | Current-day KSE substitute margin | 16 |
| CrdayKseCrdtMnyMgn | int | Current-day KSE credit cash margin | 16 |
| CrdayKseCrdtSubstMgn | int | Current-day KSE credit substitute margin | 16 |
| PrdayKdqMnyMgn | int | Previous-day KOSDAQ cash margin | 16 |
| PrdayKdqSubstMgn | int | Previous-day KOSDAQ substitute margin | 16 |
| PrdayKdqCrdtMnyMgn | int | Previous-day KOSDAQ credit cash margin | 16 |
| PrdayKdqCrdtSubstMgn | int | Previous-day KOSDAQ credit substitute margin | 16 |
| CrdayKdqMnyMgn | int | Current-day KOSDAQ cash margin | 16 |
| CrdayKdqSubstMgn | int | Current-day KOSDAQ substitute margin | 16 |
| CrdayKdqCrdtMnyMgn | int | Current-day KOSDAQ credit cash margin | 16 |
| CrdayKdqCrdtSubstMgn | int | Current-day KOSDAQ credit substitute margin | 16 |
| PrdayFrbrdMnyMgn | int | Previous-day Freeboard cash margin | 16 |
| PrdayFrbrdSubstMgn | int | Previous-day Freeboard substitute margin | 16 |
| CrdayFrbrdMnyMgn | int | Current-day Freeboard cash margin | 16 |
| CrdayFrbrdSubstMgn | int | Current-day Freeboard substitute margin | 16 |
| PrdayCrbmkMnyMgn | int | Previous-day OTC cash margin | 16 |
| PrdayCrbmkSubstMgn | int | Previous-day OTC substitute margin | 16 |
| CrdayCrbmkMnyMgn | int | Current-day OTC cash margin | 16 |
| CrdayCrbmkSubstMgn | int | Current-day OTC substitute margin | 16 |
| DpspdgQty | int | Deposited collateral quantity | 16 |
| BuyAdjstAmtD2 | int | D+2 buy settlement amount | 16 |
| SellAdjstAmtD2 | int | D+2 sell settlement amount | 16 |
| RepayRqrdAmtD1 | int | D+1 required repayment | 16 |
| RepayRqrdAmtD2 | int | D+2 required repayment | 16 |
| LoanAmt | int | Loan amount | 16 |

## Position rows and field presence

OutBlock3 carries separate position evidence. The source example has BalQty=0,
BnsBaseBalQty=1, BuyUnsttQty=1, PchsAmt=60000 and AvrUprc=60000, with
UprcTpCode=0. Preserve settlement versus trade-basis quantity and actual purchase
amount rather than multiplying a settled quantity by a BEP price. A nonempty
live holding was not available in the read-only probe; this is a documentation
fixture, not a newly executed trade.

The PnlRat example is0.378333; its table only labels it as a PnL ratio. Keep the
raw scale until explicitly established. SellPnlAmt must not be promoted to
workflow realized PnL from its name alone. RegMktCode is a registered market
code, not proof of the execution venue. SC1 venue is still unverified.

Absent fields must stay distinguishable through model_fields_set or raw keys.
Compatibility fields Expdt/SellQty/BuyQty are not in the new source and are not
aliases for DueDt or dated execution quantities. No account identifiers or
credentials from the supplied examples are retained in this reference.

## Direct recheck of the corrected request

At06:08:48 UTC on2026-09-15 the corrected official-example request, including
RecCnt=1, returned HTTP200/rsp_cd00136 and all matching selector echoes. Raw
OutBlock2 contained exactly69 keys; every one is represented in the corrected
model and marked not_provided. The parsed response retained block2_status with
that value. The position array was explicitly empty, so nonempty live position
fields remain unverified. Zero orders were submitted. This is not validation of
a trading strategy, full account totals or an undocumented response-code mapping.
