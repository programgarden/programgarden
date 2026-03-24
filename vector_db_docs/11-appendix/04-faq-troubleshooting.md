---
category: appendix
tags: [faq, troubleshooting, error, common_mistakes, credential, symbol, edge, auto_iterate, problem_solving, frequently_asked_questions]
priority: high
---

# FAQ and Troubleshooting

## Frequently Asked Questions

### Q1: What is the minimum configuration for a workflow JSON?

The minimum configuration is StartNode + one or more nodes + edges:

```json
{
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"}
    ],
    "edges": [
        {"from": "start", "to": "broker"}
    ],
    "credentials": [
        {"credential_id": "cred-1", "type": "broker_ls_overseas_stock", "data": []}
    ]
}
```

### Q2: Can I query market data without a BrokerNode?

No. MarketDataNode, AccountNode, OrderNode, and similar nodes all access the securities API through BrokerNode. BrokerNode must precede them in the DAG path.

```
start → broker → market    (O) Correct
start → market              (X) No broker - fails
```

### Q3: Can I use overseas stock and overseas futures nodes in the same workflow?

Yes. Just use separate BrokerNodes for each:

```json
{
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "stock_broker", "type": "OverseasStockBrokerNode", "credential_id": "stock-cred"},
        {"id": "futures_broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures-cred", "paper_trading": true},
        {"id": "stock_account", "type": "OverseasStockAccountNode"},
        {"id": "futures_account", "type": "OverseasFuturesAccountNode"}
    ],
    "edges": [
        {"from": "start", "to": "stock_broker"},
        {"from": "start", "to": "futures_broker"},
        {"from": "stock_broker", "to": "stock_account"},
        {"from": "futures_broker", "to": "futures_account"}
    ]
}
```

### Q4: Does the AI Agent remember conversations?

No. AIAgentNode is **Stateless**. Each execution is independent, and it does not remember conversation content from previous executions. Required data is fetched fresh each time through nodes connected via Tool edges.

### Q5: Can I connect a realtime node directly to an AI Agent?

It is possible, but `cooldown_sec` configuration is required. Realtime nodes trigger on every incoming data update, so connecting without a cooldown will result in excessive LLM calls. Directly connecting realtime nodes without a ThrottleNode is blocked.

```json
{
    "id": "agent",
    "type": "AIAgentNode",
    "cooldown_sec": 300
}
```

### Q6: Can I use credentials in dynamic nodes?

No. For security reasons, credential access via `credential_id` is blocked in dynamic nodes (`Dynamic_` prefix). If you need external API calls, use HTTPRequestNode or query data from another node and pass it to the dynamic node.

### Q7: Can I use multiple plugins in a single ConditionNode?

Only one plugin can be specified per ConditionNode. To combine multiple conditions, use LogicNode:

```json
{
    "nodes": [
        {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "fields": {"period": 14}},
        {"id": "macd", "type": "ConditionNode", "plugin": "MACD", "fields": {"fast": 12}},
        {"id": "logic", "type": "LogicNode", "operator": "all", "conditions": [
            {"is_condition_met": "{{ nodes.rsi.result.passed }}", "passed_symbols": "{{ nodes.rsi.result }}"},
            {"is_condition_met": "{{ nodes.macd.result.passed }}", "passed_symbols": "{{ nodes.macd.result }}"}
        ]}
    ]
}
```

### Q8: Do notes (memos) affect execution?

No. `notes` are sticky notes displayed on the canvas and are unrelated to workflow execution. They are used for documentation purposes only.

```json
"notes": [
    {"id": "note-1", "content": "## Strategy Memo\nRSI + MACD compound strategy", "color": 1, "width": 300, "height": 200, "position": {"x": 100, "y": 50}}
]
```

## Troubleshooting

### E1: BrokerNode Connection Failure (403 Forbidden)

**Cause**: appkey/appsecret is empty or invalid

**Solution**:
- Verify that correct credentials are passed in secrets
- Ensure credential_id matches between the workflow definition and secrets

```python
# Correct example
job = await executor.execute(
    definition=workflow,
    secrets={"broker-cred": {"appkey": "VALID_KEY", "appsecret": "VALID_SECRET"}}
)
```

### E2: Node Output is None

**Cause**: Incorrect node ID or port name in data binding

**Check**:
- Whether `nodeId` in `{{ nodes.nodeId.portName }}` matches the actual `id` field of the node
- Whether `portName` matches the actual output port name of the node

```json
{"id": "my_account", "type": "OverseasStockAccountNode"}

"data": "{{ nodes.my_account.positions }}"
```

### E3: Auto-iterate Not Working

**Cause**: Previous node output is a single value instead of an array

**Check**:
- Verify that the previous node's output is an array (List)
- Verify that `items` in ConditionNode is set to `passed_symbols`
- The `{{ item }}` keyword is only available in auto-iterate context

### E4: Overseas Futures Symbol Query Failure

**Cause**: Incorrect contract month code

Overseas futures symbols use the format: product code + contract month code:
- Month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
- Example: `HMCEG26` = E-mini S&P (HMCE) February 2026 contract (G=Feb, 26=2026)

### E5: HistoricalDataNode Date Format Error

**Cause**: `start_date`, `end_date` format is not `yyyymmdd`

```json
"start_date": "{{ date.ago(30, format='yyyymmdd') }}",
"end_date": "{{ date.today(format='yyyymmdd') }}"
```

If `format='yyyymmdd'` is not specified, the result will be in ISO format (`2026-02-14`), causing API call failure.

### E6: Conditions Not Passed to LogicNode

**Cause**: Incorrect `conditions` array format

```json
{
    "id": "logic",
    "type": "LogicNode",
    "operator": "all",
    "conditions": [
        {"is_condition_met": "{{ nodes.rsi_condition.result.passed }}", "passed_symbols": "{{ nodes.rsi_condition.result }}"},
        {"is_condition_met": "{{ nodes.macd_condition.result.passed }}", "passed_symbols": "{{ nodes.macd_condition.result }}"}
    ]
}
```

`conditions` must be an array of objects containing `is_condition_met` (whether the condition is met) and `passed_symbols` (passed symbols).

### E7: Order Node Duplicate Execution

**Cause**: Retry (resilience) is enabled on the order node

Order nodes have retry disabled by default due to the risk of duplicate orders. If retry is intentionally enabled, duplicate orders may occur.

### E8: AI Agent Tool Call Failure

**Cause**: The node connected via Tool edge has not executed yet or the connection type is wrong

Verify Tool edge connection:
```json
{"from": "account", "to": "agent", "type": "tool"}
```

If `type: "tool"` is not specified, it is treated as a default `main` edge and will not be registered as a Tool.

### E9: Realtime Workflow Does Not Stop

**Cause**: Workflows containing realtime nodes (RealMarketDataNode, etc.) must call `job.stop()` to terminate

```python
job = await executor.execute(workflow)
# ... receiving realtime data ...
await job.stop()  # Explicit stop
```

### E10: Nested Field Access Failure in Expressions

**Cause**: Attempting to use bracket notation instead of dot notation

```json
"price": "{{ item.order.price }}"
```

In expressions, use dot notation `item.order.price` instead of `item['order']['price']`.

## Symbol Data Format Notes

Symbol data must always use the array + `symbol`/`exchange` field format:

```json
[
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "exchange": "NASDAQ"}
]
```

Do not use symbols as dictionary keys:

```json
{"AAPL": {"exchange": "NASDAQ"}}
```
