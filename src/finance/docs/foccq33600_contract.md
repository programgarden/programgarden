# FOCCQ33600 source and observation limits

Source: LS OpenAPI table and example supplied by the owner on2026-09-15.
POST /stock/accno, one request/second per shared app key. Input QrySrtDt and
QryEndDt are dates of length8. TermTp has length1:1 daily,2 weekly,3 monthly.
The official example also sends RecCnt=1 despite its omission from the input
table; the SDK now retains and documents it.

OutBlock1 fields are RecCnt, AcntNo, Pwd, QrySrtDt, QryEndDt and TermTp.
Account/password echoes are sensitive and must not be logged or published.
OutBlock2 provides RecCnt, AcntNm, BnsctrAmt, MnyinAmt, MnyoutAmt,
InvstAvrbalPramt, InvstPlAmt and InvstErnrat. The supplied omission instruction
applies to CSPAQ12300OutBlock2 only, not to this TR's summary.

OutBlock3 fields are BaseDt, FdEvalAmt, EotEvalAmt, InvstAvrbalPramt,
BnsctrAmt, MnyinSecinAmt, MnyoutSecoutAmt, EvalPnlAmt, TermErnrat and Idx.
Monetary field labels do not establish the complete product coverage or exact
return calculation. Keep the broker-reported rate and source dates; do not
substitute the futures midpoint estimate or claim a domestic-only series from
the SDK directory name. The publication time of current-day reports is unknown.

The supplied request and response examples contain different date ranges. They
are source-shape examples, not one verified request/response pair. The response
message says more data remains; it does not establish a complete report. Check
actual continuation headers and requested/echoed/row dates independently.

Direct source recheck at06:08:51 UTC on2026-09-15 used RecCnt=1, dates20260908
through20260915 and TermTp=1. HTTP200/rsp_cd00136 returned all matching request
echoes and an explicit7-row array dated September8–14. September15 was absent.
There was no SDK error and no order was submitted. This confirms those observed
fields/dates, not a full historical series or the unstated accounting rules.
