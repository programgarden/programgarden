# CDPCQ04700: schema, field presence and deposit evidence

Reviewed against the LS REST guide on 2026-09-21:
https://openapi.ls-sec.co.kr/guide/api/047x41xg-k554-3j5w-834d-1qml538oh06m?type=rest&api=37d22d4d-83cd-40a4-a375-81b010a4a627
Public guide: https://openapi.ls-sec.co.kr/apiservice?api_id=37d22d4d-83cd-40a4-a375-81b010a4a627

The owner's `ls-openapi-tr-guides.json` export was compared field by field with
the live guide: all seven request fields and 111 response fields match in
name, type, length, label and description. The sanitized fixture records the
response schema; it contains no broker example account data.

The endpoint is `/stock/accno`, limited to one request per second. The REST
contract has five response blocks with 10, 2, 78, 4 and 17 fields respectively.
This count describes the current response tables, not a live response.
The previous SDK modeled only a subset and discarded blocks 4/5 and unmodeled
detail fields. A field absent from that parsed model therefore did not prove
that the broker omitted it. The SDK now retains all documented fields, unknown
block fields and the original JSON in `response.raw_payload`.

## Query scope

- `QryTp`: `0` all, `1` cash deposits/withdrawals, `2` security transfers,
  `3` trades, `4` currency exchange, `9` other.
- `PdptnCode`: the reviewed REST table specifies `01`.
- `IsuLgclssCode`: `00` all, `01` stock, `02` bonds, `03` futures, `04` funds,
  `05` overseas stocks, `06` overseas derivatives.
- The SDK default asset class is `01`. It is not an all-asset query.
- `SrtNo=0` is the initial official example. The table does not establish a
  complete pagination algorithm. Preserve continuation headers and refuse a
  completeness claim when additional pages are indicated.
- The directory `example/korea_stock/` identifies the API route group. It does
  not prove or disprove whether an authenticated overseas-stock account works.

## Do not turn absent data into financial facts

`model_fields_set` records explicitly present fields. Newly added optional
numeric fields distinguish missing/`None`, blank `""`, and zero. Existing
defaults remain for compatibility, so `row.AdjstAmt == 0` alone is not proof
of a returned zero; first require `"AdjstAmt" in row.model_fields_set`.
`model_dump(exclude_unset=True)` helps retain this distinction.
Missing `block3` has the legacy value `[]` but is absent from the response's
`model_fields_set`. Explicit empty arrays remain present. Malformed blocks
return an `error_msg` and must not be consumed as successful empty history.

`raw_payload` is a defensive copy of the received JSON and is excluded from
normal `model_dump()` and repr. It can contain account identifiers and names.
Keep authorized diagnostic captures in private files, never console logs,
Git commits, chatbot prompts or public fixtures.

## What still needs a controlled observation

No actual before/after cash-deposit response is established by this document.
Neither documented fields nor a successful HTTP response prove reliable cash
transfer detection across products, dates or currencies.

- Detail evidence: `TrdDt`, `TrdNo`, `SmryNo`, `SmryNm`, `TpCodeNm`,
  `CancTpNm`, `OrgTrdNo`, `TrxTime` and the actual returned amounts.
- `DpsBfbalAmt` is a prior balance, not a deposit amount. `AdjstAmt` must not
  silently be interpreted as USD.
- Foreign-currency evidence also needs explicit `CrcyCode` and populated
  `FcurrAmt`, `FcurrTrdAmt` or `FcurrAdjstAmt`, with their meaning checked
  against the known transfer. Currency exchange is distinct from external
  funding of the whole account. For a USD-only portfolio, a verified KRW-to-USD
  conversion can instead be capital entering that measured currency scope.
  Link it to the originating cash flow; never count both legs as new capital
  or assume that a KRW transfer alone establishes the resulting USD amount.
- Aggregate `block5.MnyinAmt/MnyoutAmt` do not identify a currency. Their
  presence, sign, date scope, units and reliability require observation.
- Cancellation/reversal, duplicate IDs and nonterminal pages prevent naive
  summation. One successful transfer proves that case, not general coverage.

If fields are absent or ambiguous, report funding as unverified. An unexplained
balance change minus trade PnL is a reconciliation signal, not authoritative
deposit evidence. Do not automatically rebase returns from that residual.

## Earlier observations and their limits

An internal September 10, 2026 observation report describes 146 rows across five
pages on one live account. It reports 42 fields blank or zero throughout, partial
currency-code population, and currency conversion classified as a withdrawal
while the USD balance increased. Its observed summary codes include 1777
(real-time bank-transfer deposit), 1512 (foreign-currency transfer in), and 2923
(margin-related currency purchase). These are case observations, not an official
universal code map or a fresh review of the raw ledger. Do not infer sign, currency,
or externally supplied capital from a summary label alone. A present zero is
still different from a field omitted by the broker.

Inspect existing authorized transfer/conversion records before requesting a
new controlled transfer. Recheck raw amount, currency, reversal state and account
identity; a summary report alone does not establish those fields.

## Directly rechecked sparse responses (September 21, 2026)

Two read-only requests on the same authorized live account checked a known
transfer day (`QryTp=1`) and a bounded currency-conversion period (`QryTp=4`).
Both used asset class `00`, echoed all seven query fields, returned `00136`,
and ended with `tr_cont=N` and an empty continuation key. No token issuance,
orders or deposits were performed by these two captures. The SDK preserved
all returned fields without a parse error. Amounts and account identities are
omitted here; the regression fixture uses synthetic values.

- The transfer row had summary code `1777`, normal cancellation status, an
  explicit transaction number and **blank `CrcyCode`**. `TrdAmt` and `AdjstAmt`
  were both explicitly zero. The unprefixed deposit-balance increase exactly
  matched `OutBlock5.MnyinAmt` **and `FcurrTrdAmt`**. Both foreign balances were
  zero. Thus even a positive field named `FcurrTrdAmt` does not establish USD;
  do not silently substitute zero from the generic transaction/settled fields.
- Two conversion rows had code `2923`, `CrcyCode=USD`, a withdrawal display
  label, decreasing domestic balances and **increasing USD balances**. The USD
  increase matched `FcurrTrdAmt`; `FcurrAdjstAmt` was zero.
- A third row returned within the conversion query had code `1512`, explicit
  USD, an incoming label, positive exchange rate and a USD balance increase
  matching `FcurrTrdAmt`. Its domestic balance did not change. The raw row alone
  therefore does not identify or reconcile the originating counter-leg.

These observations establish these rows, not a universal summary-code map or
complete lifetime funding history. Terminal continuation covers the requested
mode and date range; a conversion-only scan excludes other modes. Connecting
the transfer to later currency conversions requires the intervening ledger.
Keep whole-account external transfers separate from flows into a USD-only scope.

## Bounded diagnostic example

`example/korea_stock/run_CDPCQ04700.py` uses an explicit private token file with
`access_token` and a timezone-aware ISO `expires_at`, supplied by the existing
token issuer. No token issuance, dotenv loading, order, pagination or automatic
retry occurs. It sends one direct POST because the ordinary SDK `req()` transport
can automatically retry transient errors and request token renewal. Coordinate
the shared key's rate limit before each separate invocation.

Use `--dry-run` to inspect the query without credentials or network. A real capture
requires a new `--output` file and writes it with mode 0600. Original JSON, selected
continuation headers and parse/transport status are kept privately; the console
contains status only. Continuation or missing evidence must not be called a
complete funding history. Offline regression fixtures are not live validation.
