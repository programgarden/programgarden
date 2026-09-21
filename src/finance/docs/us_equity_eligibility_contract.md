# US equity eligibility and dividend evidence

Reviewed against the owner-supplied LS guide export `20260918015713008` on
September 21, 2026. g3104 defines 34 output fields. g3190 defines five control
fields and 30 issue fields. Every field name already exists in the SDK.
This comparison does not establish actual population or undocumented enum values.

## Listing and trading status

- g3190 `expire_date` is labelled **expiry date**, not delisting date. It cannot
  establish delisting, its effective time or an eligible/excluded position.
  Earlier SDK English metadata conflated expiry and delisting; this is corrected.
- g3190 `suspend` and g3104 `suspend` are status fields without a documented code
  map in this export. Example values must not be treated as that missing map.
  `sellonly` is not an independently documented halt/delisting indicator.
- Neither status flag supplies the effective halt/resumption time. g3190 `bymd`
  is a business date, not an event timestamp. A daily snapshot or later fetch
  cannot prove when an intraday status change occurred.
- Missing master rows, missing/blank status fields and expiry sentinels do not
  establish normal trading or delisting. Model defaults are not observed fields;
  consumers must retain response/field presence separately.
- `exchcd`/listing identity need an authoritative market map before classifying
  US OTC equities. Do not infer OTC from LS noncoverage, a reusable ticker, or
  an off-exchange execution of an exchange-listed security.

For prospective contest exclusions, separately preserve the effective event,
same-instrument lot/valuation evidence and prior realized/unrealized performance.
Never set a missing position price to zero or retrospectively erase earlier
performance when a halt/delisting is observed later.

## Account dividends

CDPCQ04700 OutBlock3 includes `MnyDvdAmt`, `FcurrTaxSumAmt` and transaction,
currency and cash fields. The field labels alone do not establish a USD dividend
credit or gross/net amount. Values can be omitted, blank or zero. See the
[observed CDPCQ04700 contract](cdpcq04700_contract.md).

A reviewed dividend effect requires account scope, original transaction identity,
actual currency, cash credit, associated withholding and cancellation/reversal
reconciliation. Neither a positive foreign-named field nor an account balance
residual is sufficient. Company dividend announcements are not account receipts.
Do not classify dividends as capital deposits, and do not deduct both the
dividend and its withholding twice. Reinvestment does not erase the payment.

No actual dividend credit or authoritative LS halt enum was verified in this
audit. The SDK retains evidence and states limitations; it does not certify
contest eligibility or adjust customer trading/account balances.
