# Overseas-stock sell capacity

The REST `OverseasStockAccountNode.positions` output now includes `sellable_qty`
from the existing COSOQ00201 OutBlock4 `AstkSellAbleQty` field. The account query
and its request parameters are unchanged; this adds no broker request.

`quantity` and `qty` remain the total holding quantity. Sell capacity is separate:
a holding of seven shares can have three, zero or a fractional quantity available
to sell. No subtraction from holdings or open orders is used to invent capacity.
If the raw broker field was absent, the output is null even though the finance
model has a default zero. A returned zero remains zero. Consumers must block a
capacity-dependent order when that value is unavailable or invalid.

This is a snapshot for workflow checks, not an order reservation or a guarantee
that a later broker request will be accepted. The live account tracker and other
products are unchanged. The catalog exposes the same field for authoring.

Offline tests use the actual SDK model and assert observed positive, zero,
fractional and missing values independently of holdings. They also check the
consumed field names against that model and preserve the SDK example's request
filters. No credentials, broker request or order is used by these tests.

Status: unreleased source correction after 2.5.1. A new engine/core release and
consumer pins are required before claiming this field in deployed runtimes.
