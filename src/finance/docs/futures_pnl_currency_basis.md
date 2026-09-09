# Futures PnL currencies and monetary basis

Futures account tracking separates two different observations:

- `broker_pnl_amount` preserves the supplied `CIDBQ01500.AbrdFutsEvalPnlAmt`,
  including zero and negative values. `broker_pnl_basis` is always
  `broker_reported_unconfirmed`: the available broker field description does
  not establish its monetary unit, mark basis or included costs. A missing
  response field remains `None`, even when the SDK model has a zero default.
- `pnl_amount` is a **native-currency gross price-change estimate** from entry
  price, latest price, quantity and a compatible contract's tick metadata.
  `pnl_currency`, `pnl_basis="estimated_gross_price_change"`, and
  `pnl_status="available"` describe this amount. It is not broker net PnL,
  settlement PnL, account equity, return or MDD. REST refreshes and realtime
  ticks use this same basis; neither substitutes an estimated USD fee result
  for the preserved broker amount.

When price/currency/spec/tick evidence is missing or incompatible,
`pnl_amount`, `pnl_currency` and `pnl_basis` are `None`, `pnl_status` is
`"unavailable"`, and `pnl_unavailable_reason` describes the missing evidence.
The existing position `currency` field retains the observed position code; it
does not prove the broker amount's unit. The legacy `realtime_pnl` field remains
for API compatibility, but the account tracker no longer populates it with a
fee-adjusted USD estimate. Position `pnl_rate` remains the existing nominal
price-change percentage; it is not an account-equity return.
The tracker still accepts `commission_rate` for constructor compatibility;
it is not applied to the native gross estimate or preserved broker amount.

## Standalone calculations

`extension.calculator.calculate_futures_pnl` and
`FuturesPnLCalculator.calculate_realtime_pnl` retain the existing **USD-only
estimator** behavior for valid USD specifications. Its round-trip fee, tax and
USD/KRW values are estimates, not observed broker charges. Passing a non-USD
or blank-currency spec raises `usd_estimator_requires_usd_spec`. Invalid or
zero tick metadata is rejected instead of used as evidence.

Manual tick inputs in this legacy estimator retain the USD default, made
explicit by `FuturesTradeInput.manual_currency="USD"`. Non-USD manual values
are rejected. Supplying USD manual overrides does not silently convert or
override a contradictory non-USD contract specification.

For a separate native gross estimate, import:

```python
from decimal import Decimal
from programgarden_finance.ls.overseas_futureoption.extension.calculator import (
    calculate_native_gross_pnl,
)
from programgarden_finance.ls.overseas_futureoption.extension.symbol_spec_manager import SymbolSpec

contract = SymbolSpec(
    symbol="SYNTHETIC_HKD", currency="HKD", tick_size=Decimal("1"),
    tick_value=Decimal("10"),
)
estimate = calculate_native_gross_pnl(
    spec=contract, quantity=1, entry_price=Decimal("25000"),
    current_price=Decimal("25001"), is_long=True,
)
assert estimate.amount == Decimal("10")
assert estimate.currency == "HKD"
assert estimate.basis == "estimated_gross_price_change"
```

`FuturesNativePnLResult` contains `amount`, `currency`, `basis`, `total_ticks`,
`tick_size_used` and `tick_value_used`. This function applies no fee, tax, FX,
margin or quote-adjustment assumption. Short positions reverse the price
movement sign. Metadata must actually apply to the quoted instrument; the
function does not establish broader broker accounting semantics.

## Account totals

`AccountPnLInfo.pnl_by_currency` maps each currency to a
`FuturesCurrencyPnL(currency, basis, total_pnl_amount, position_count)` subtotal
of **available compatible estimates only**. `unavailable_position_count`
records excluded positions. These subtotals must not be described as complete
account financial valuations when any position is unavailable.

Legacy `total_pnl_amount`, `currency` and `pnl_basis` are available only when
all positions have compatible available estimates in a single currency.
Mixed currencies, unknown positions or incompatible bases make those scalars
`None` with `pnl_status="unavailable"`. Zero and negative *known* estimates
remain available; unknown is never silently zero or USD. An empty account is
unavailable with reason `no_positions`.

`account_pnl_rate`, `total_eval_amount` and `total_margin_used` remain `None`:
the account model does not have enough evidence to combine raw margins,
valuation bases and return denominators safely. Raw position margins remain
available as broker fields, without invented cross-currency aggregation.

## Missing master metadata and compatibility

`SymbolSpec.currency` retains its USD default for existing manually constructed
USD specs. Actual `o3121` rows explicitly preserve blank `CrncyCd` as an empty
currency; missing or zero `UntPrc` and `MnChgAmt` remain zero. The manager no
longer invents USD, tick-size0.01 or tick-value1 for missing broker metadata.
Native and USD calculators reject those missing/invalid inputs. Valid supplied
metadata is unchanged.

Consumers must carry amount, currency, basis and availability together.
REST position estimates also require explicitly supplied `PchsPrc`, `BalQty`
and a recognized `BnsTpCode` (1 sell, 2 buy). A subsequent price tick cannot
repair missing quantity, entry or direction evidence. An explicit zero quantity
is distinct from a missing quantity defaulted to zero by the response model.
Coercing `None` through `or0`, defaulting currency to USD, mixing currency
subtotals or filling unknown account-return fields from price×quantity loses
this contract. Executor/context/event forwarding need the corresponding
consumer integration before an application can claim this SDK change fixes
its complete monetary reporting path.
