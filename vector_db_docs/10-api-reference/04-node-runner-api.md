---
category: api_reference
tags: [api, node_runner, standalone, standalone_execution, NodeRunner, run, credential, broker, market_data, account_query]
priority: high
---

# NodeRunner API

## Overview

NodeRunner is a lightweight API for executing individual nodes standalone without creating a workflow. It automatically handles broker login, credential injection, and connection creation.

## Basic Usage

```python
from programgarden import NodeRunner

# Simple node execution
runner = NodeRunner()
result = await runner.run("HTTPRequestNode", url="https://api.example.com", method="GET")

# Broker-dependent node execution (auto LS login)
async with NodeRunner(credentials=[
    {"credential_id": "broker", "type": "broker_ls_overseas_stock",
     "data": {"appkey": "...", "appsecret": "..."}}
]) as runner:
    result = await runner.run("OverseasStockMarketDataNode",
        credential_id="broker",
        symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        fields=["price", "volume"]
    )
```

## Constructor

```python
NodeRunner(
    credentials=None,        # Credential list (same format as workflow JSON credentials)
    context_params=None,     # Execution context parameters
    raise_on_error=True,     # Whether to raise RuntimeError on error
)
```

## Methods

### run()

```python
await runner.run(
    node_type: str,              # Node type name
    node_id: str = None,         # Node ID (auto-generated)
    credential_id: str = None,   # Credential ID
    **config,                    # Node configuration
) -> dict
```

### list_node_types()

Returns a list of available node types. Excludes realtime/BrokerNode types.

### get_node_schema()

Returns the configuration schema of a node. Allows checking which parameters can be passed.

### cleanup()

Cleans up resources. Automatically called when using the `async with` pattern.

## Processing by Node Type

| Type | Example | Credential Required | Description |
|------|---------|:---:|-------------|
| Simple | HTTPRequestNode, FieldMappingNode | No | Only pass configuration |
| Credential | HTTPRequestNode(Bearer) | Yes | Pass credentials array |
| Broker-dependent | MarketDataNode, AccountNode | Yes | Auto LS login + connection injection |
| Realtime | RealMarketDataNode | - | Not supported (ValueError) |

## credential type Rules

| type | Behavior | product |
|------|----------|---------|
| `broker_ls_overseas_stock` | Auto LS login | overseas_stock (live only) |
| `broker_ls_overseas_futures` | Auto LS login | overseas_futures (paper trading available) |
| Other (telegram, http_bearer, etc.) | Credential injection only | N/A |

## Error Handling

- `raise_on_error=True` (default): Raises `RuntimeError` if the node result contains an error
- `raise_on_error=False`: Returns the result as-is even if an error exists

## Broker Session Reuse

When executing multiple nodes within the same NodeRunner instance, the LS login session is reused.

```python
async with NodeRunner(credentials=[...]) as runner:
    # First call performs LS login
    market = await runner.run("OverseasStockMarketDataNode", credential_id="broker", ...)
    # Second call reuses existing session (no login)
    account = await runner.run("OverseasStockAccountNode", credential_id="broker")
```

## Full Example

```python
import asyncio
from programgarden import NodeRunner

async def main():
    credentials = [{
        "credential_id": "broker",
        "type": "broker_ls_overseas_stock",
        "data": {"appkey": "...", "appsecret": "..."},
    }]

    async with NodeRunner(credentials=credentials) as runner:
        # Query current price
        market = await runner.run("OverseasStockMarketDataNode",
            credential_id="broker",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            fields=["price", "volume", "change_pct"],
        )
        print(f"AAPL: ${market['values'][0]['price']}")

        # Query fundamentals
        fund = await runner.run("OverseasStockFundamentalNode",
            credential_id="broker",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            fields=["per", "eps", "market_cap"],
        )
        print(f"PER: {fund['values'][0]['per']}")

        # Query account balance
        account = await runner.run("OverseasStockAccountNode",
            credential_id="broker",
        )
        print(f"Holdings: {account['count']} positions")

asyncio.run(main())
```
