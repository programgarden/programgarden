# Order node contracts

New, modify and cancel order nodes use direct fields. They do not use
MarketOrder, LimitOrder, TrailingStop or TimeStop order plugins.

## Sizing and multiple orders

PositionSizingNode consumes `symbols`, `balance`, and matching quote rows in
`market_data`. Candidates may instead carry their own positive `price`.
`method` is required: fixed_percent, fixed_amount, fixed_quantity, kelly or
atr_based. There is no default method and no risk_parity method.

The canonical output is `orders`, an array of objects containing symbol,
exchange, quantity and price. The deprecated `order` alias contains only the
first result; using it for multiple candidates can repeat or omit orders.
Connect sizing to the order node with `from_port: "orders"`, then bind the order
node's `order` field to `{{ item }}`. The execution edge and expression are both
necessary. An empty orders array is a normal no-order result; never fall back to
the candidate symbols to invent a quantity.

For fixed_percent, the total budget is balance * max_percent / 100, divided
across candidates. With balance727, max_percent10 and two candidates, each gets
36.35. If each whole share costs more, no order is produced. Do not raise the
allocation or quantity without the user's requested strategy change.

```json
{
  "nodes": [
    {"id": "sizing", "type": "PositionSizingNode",
     "symbols": "{{ nodes.candidates.symbols }}",
     "balance": "{{ nodes.account.balance }}",
     "market_data": "{{ nodes.quotes.values }}",
     "method": "fixed_percent", "max_percent": 10},
    {"id": "buy", "type": "OverseasStockNewOrderNode", "side": "buy",
     "order_type": "limit", "price_type": "limit", "order": "{{ item }}"}
  ],
  "edges": [
    {"from": "account", "to": "sizing"},
    {"from": "candidates", "to": "sizing"},
    {"from": "quotes", "to": "sizing"},
    {"from": "sizing", "to": "buy", "from_port": "orders"}
  ]
}
```

This is a pipeline fragment: define the referenced account, candidates, quote
and broker nodes in the complete workflow. Account and quote dependencies must
complete before sizing. Preserve session, holdings, pending-order and durable
reservation guards when adapting a guarded strategy.

## New orders

Use the product-specific OverseasStockNewOrderNode,
OverseasFuturesNewOrderNode or KoreaStockNewOrderNode. `order` must resolve to
one object, not a symbol string or a list. The object carries `symbol`,
`exchange`, positive quantity and, when required by the order type, price.
A resolved object binding (`{{ item }}`) and an object whose leaf values are
bindings are both supported. UI expression_only metadata does not prohibit the
latter runtime shape.

`order_type` and `price_type` are fixed enum strings. For overseas stocks,
price_type accepts limit, market, LOO, LOC, MOO and MOC. A numeric quote or
`{{ item.price }}` belongs in `order.price`, never in price_type. Use the
selected product's registered schema for its order modes and actual tick rules.
Do not infer broker acceptance or fills from a simulated result.

## Closing held positions

Quantity must come from the selected account positions. Account nodes are not
implicit iteration sources: connect `from_port: "positions"` explicitly when
iterating their positions. For a conditional exit, keep the signal filter on
the order path and use the filter's output instead.

SymbolFilterNode intersection preserves input_a fields. Put positions in
input_a and matching signals in input_b to retain quantity/current_price.
WatchlistNode normalizes to symbol/exchange and drops quantity, so it must not
sit between the selected positions and an order relying on item.quantity.

```json
{
  "id": "sell", "type": "OverseasStockNewOrderNode", "side": "sell",
  "order_type": "market",
  "order": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
            "quantity": "{{ item.quantity }}"}
}
```

For futures, use the position's verified close_side rather than assuming every
position closes with sell. Retain product/account mode and pending-order guards.
The engine submits whole quantities; a fractional-only position is not evidence
that a full liquidation happened.

## Modify and cancel

Identify the target with `original_order_id`, `symbol` and `exchange` from the
account's current open orders. Modify supports `new_quantity` and `new_price`.
Cancel supports the product's quantity contract. Read the product schema before
constructing requests. The input is original_order_id, not order_id; order_id
is the upstream output to bind from. Maintain account/execution ownership and
confirm the resulting state with broker evidence.

## Indicator and validation evidence

Historical `values` contains per-symbol wrappers with a nested `time_series`.
An iterated ConditionNode reads `items.from: "{{ item.time_series }}"`; its
extract uses item.symbol/item.exchange and row.date/row.close. A wrapper itself
has no date or close. MovingAverageCross's passed_symbols reflects the current
short/long-average state; a crossing event is a different strategy.

Static validation rejects invalid fixed price/order types. Deep validation
checks resolved new-order payloads, missing sizing inputs, missing extracted
bar fields and failed indicator/iteration executions before reporting success.
A negative signal can be exercised for downstream validation, but all-error
indicator results cannot be promoted to successful signals. Default historical
fixtures contain64 bars: supply a longer explicit fixture when the indicator
needs more history. A fixture limitation does not prove the live strategy is
incorrect. Plain dry_run remains a simulation, not full payload validation.

These checks cannot prove a broker will accept or fill an order. Keep the
customer's graph unchanged during diagnosis unless they authorize a strategy
edit. Use `count()` for node-output proxy counts; bare `.count` is a method.
