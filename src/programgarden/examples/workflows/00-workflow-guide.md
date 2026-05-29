# ProgramGarden Workflow JSON Guide

This guide covers everything needed to construct a valid ProgramGarden workflow JSON.

---

## 1. JSON Structure

A workflow JSON has these top-level fields:

```json
{
  "id": "my-workflow",
  "name": "Workflow display name",
  "description": "What this workflow does",
  "nodes": [],
  "edges": [],
  "credentials": [],
  "notes": []
}
```

### Node

```json
{
  "id": "unique_node_id",
  "type": "OverseasStockAccountNode",
  "credential_id": "broker_cred",
  "position": { "x": 100, "y": 200 },
  "...": "node-specific fields"
}
```

- `id`: Unique identifier within the workflow. **Must use underscores, not hyphens** (hyphens are parsed as subtraction in expressions).
- `type`: Registered node type name.
- `credential_id`: (Optional) References a credential defined in the `credentials` array.
- `position`: (Optional) Canvas position for UI rendering.

### Edge

```json
{ "from": "broker", "to": "account" }
```

With conditional branching (IfNode):
```json
{ "from": "if_check", "to": "order", "from_port": "true" }
```

Or using dot notation (equivalent):
```json
{ "from": "if_check.true", "to": "order" }
```

With non-default edge type (AI Agent):
```json
{ "from": "llm", "to": "agent", "type": "ai_model" }
{ "from": "market", "to": "agent", "type": "tool" }
```

Edge types:
| Type | Usage | Default |
|------|-------|---------|
| `main` | DAG execution order | Yes (omit `type` field) |
| `ai_model` | LLMModelNode → AIAgentNode connection | No |
| `tool` | Register a node as AIAgentNode tool | No |

### Credential

```json
{
  "credential_id": "broker_cred",
  "type": "broker_ls_overseas_stock",
  "data": [
    { "key": "appkey", "value": "", "type": "password", "label": "App Key" },
    { "key": "appsecret", "value": "", "type": "password", "label": "App Secret" }
  ]
}
```

### Note (Sticky Note)

```json
{
  "id": "note_1",
  "content": "## Markdown content",
  "color": 1,
  "width": 300,
  "height": 200,
  "position": { "x": 100, "y": 50 }
}
```

Notes are canvas annotations only. They are not executed.

---

## 2. Credential Types

### Broker Credentials

| Type | Name | Required Fields |
|------|------|-----------------|
| `broker_ls_overseas_stock` | LS Securities Overseas Stock | appkey (password), appsecret (password) |
| `broker_ls_overseas_futures` | LS Securities Overseas Futures | appkey (password), appsecret (password) |
| `broker_ls_korea_stock` | LS Securities Korea Stock | appkey (password), appsecret (password) |

> Note: `broker_ls_korea_stock` is used by KoreaStock workflow JSONs but may not yet be registered in the builtin credential schema on all branches.

### Messaging Credentials

| Type | Name | Required Fields |
|------|------|-----------------|
| `telegram` | Telegram Bot | bot_token (password), chat_id (text) |
| `slack` | Slack Webhook | webhook_url (password) |
| `discord` | Discord Webhook | webhook_url (password) |

### LLM Credentials

| Type | Name | Required Fields | Optional Fields |
|------|------|-----------------|-----------------|
| `llm_anthropic` | Anthropic (Claude) | api_key (password) | base_url (text) |
| `llm_openai` | OpenAI (GPT) | api_key (password) | organization (text), base_url (text) |
| `llm_azure_openai` | Azure OpenAI | api_key (password), base_url (text) | api_version (text, default: 2024-02-01) |
| `llm_deepseek` | DeepSeek | api_key (password) | — |
| `llm_google` | Google Gemini | api_key (password) | — |
| `llm_ollama` | Ollama (Local) | base_url (text, default: http://localhost:11434) | — |

### HTTP Auth Credentials

| Type | Name | Required Fields |
|------|------|-----------------|
| `http_bearer` | Bearer Token | token (password) |
| `http_header` | Custom Header | header_name (text), header_value (password) |
| `http_basic` | Basic Auth | username (text), password (password) |
| `http_query` | Query Parameter | param_name (text), param_value (password) |
| `http_custom` | Custom HTTP Auth | Dynamic key-value pairs |

### Which Nodes Use Credentials

| Node | Credential Type |
|------|----------------|
| OverseasStockBrokerNode | `broker_ls_overseas_stock` |
| OverseasFuturesBrokerNode | `broker_ls_overseas_futures` |
| KoreaStockBrokerNode | `broker_ls_korea_stock` |
| LLMModelNode | `llm_anthropic`, `llm_openai`, `llm_deepseek`, `llm_google`, etc. |
| HTTPRequestNode | `http_bearer`, `http_header`, `http_basic`, `http_query`, `http_custom` |
| TelegramNode | `telegram` |

### Credential JSON Template

```json
"credentials": [
  {
    "credential_id": "broker_cred",
    "type": "broker_ls_overseas_stock",
    "data": [
      { "key": "appkey", "value": "", "type": "password", "label": "App Key" },
      { "key": "appsecret", "value": "", "type": "password", "label": "App Secret" }
    ]
  },
  {
    "credential_id": "telegram_cred",
    "type": "telegram",
    "data": [
      { "key": "bot_token", "value": "", "type": "password", "label": "Bot Token" },
      { "key": "chat_id", "value": "", "type": "text", "label": "Chat ID" }
    ]
  },
  {
    "credential_id": "llm_cred",
    "type": "llm_anthropic",
    "data": [
      { "key": "api_key", "value": "", "type": "password", "label": "API Key" }
    ]
  }
]
```

---

## 3. Expression Syntax

Expressions use `{{ }}` delimiters to bind data between nodes.

### Node Output Reference

```
{{ nodes.<nodeId>.<port> }}
```

Examples:
```
{{ nodes.account.balance }}
{{ nodes.account.positions }}
{{ nodes.watchlist.symbols }}
{{ nodes.market.value }}
{{ nodes.rsi_condition.passed_symbols }}
```

### Auto-iterate Keywords

| Keyword | Description | Example |
|---------|-------------|---------|
| `item` | Current iteration item | `{{ item.symbol }}` |
| `index` | Current index (0-based) | `{{ index }}` |
| `total` | Total item count | `{{ total }}` |

### Method Chaining

```
{{ nodes.account.all() }}
{{ nodes.account.first() }}
{{ nodes.account.filter('pnl > 0') }}
{{ nodes.account.map('symbol') }}
{{ nodes.account.sum('quantity') }}
{{ nodes.account.avg('pnl') }}
{{ nodes.account.count() }}
{{ nodes.account.filter('pnl > 0').count() }}
```

### Function Namespaces

| Namespace | Functions | Example |
|-----------|-----------|---------|
| `date` | today(), ago(), later(), months_ago(), year_start(), year_end(), month_start() | `{{ date.ago(30, format='yyyymmdd') }}` |
| `finance` | pct_change(), pct(), discount(), markup(), annualize(), compound() | `{{ finance.pct_change(100, 110) }}` |
| `stats` | mean(), avg(), median(), stdev(), variance() | `{{ stats.mean([1,2,3]) }}` |
| `format` | pct(), currency(), number() | `{{ format.pct(12.34) }}` |
| `lst` | first(), last(), count(), pluck(), flatten() | `{{ lst.pluck(items, 'name') }}` |

---

## 4. Auto-iterate

When a node outputs an **array** and the downstream node binds with `{{ item }}`, the downstream node automatically executes once per array element.

### Trigger Conditions

Both must be true:
1. Upstream node output is an array (e.g., WatchlistNode `symbols`, SymbolFilterNode `symbols`)
2. Downstream node has a field bound to `{{ item }}` or `{{ item.xxx }}`

### Example Chain

```
[WatchlistNode] ─(symbols: [{AAPL}, {TSLA}, {NVDA}])─→ [HistoricalDataNode symbol="{{ item }}"]
                                                          Executes 3 times (one per symbol)
```

### Rules

- Empty array (`[]`) does NOT trigger auto-iterate. The downstream node runs once normally (item is undefined).
- Multiple incoming edges: only one edge should be the auto-iterate source. Mixing multiple array sources causes ambiguity.
- IfNode does NOT pass through arrays. It outputs only `true`/`false`/`result`. Do not use IfNode as a data gate in an auto-iterate chain.

---

## 5. ConditionNode Items Mapping

ConditionNode uses plugins (RSI, MACD, etc.) and requires a special `items` field to map historical data.

### Structure

```json
{
  "type": "ConditionNode",
  "plugin": "RSI",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}",
      "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}",
      "close": "{{ row.close }}"
    }
  },
  "fields": {
    "period": 14,
    "threshold": 30,
    "direction": "below"
  }
}
```

### How It Works

1. `items.from` — Points to the time series array (e.g., `{{ item.time_series }}` from HistoricalDataNode)
2. `items.extract` — Maps each row in the array to a flat record:
   - **`{{ item.xxx }}`** — External context (evaluated once, applied to all rows). Used for `symbol`, `exchange`.
   - **`{{ row.xxx }}`** — Per-row field from the time series. Used for `date`, `close`, `open`, `high`, `low`, `volume`.
3. `fields` — Plugin-specific parameters (period, threshold, etc.)

### Required Extract Fields

| Field | Source | Required By |
|-------|--------|-------------|
| symbol | `{{ item.symbol }}` | All plugins |
| exchange | `{{ item.exchange }}` | All plugins |
| date | `{{ row.date }}` | All plugins |
| close | `{{ row.close }}` | Most plugins |
| open | `{{ row.open }}` | Some plugins (e.g., CandlestickPattern) |
| high | `{{ row.high }}` | Some plugins (e.g., BollingerBands, Ichimoku) |
| low | `{{ row.low }}` | Some plugins (e.g., BollingerBands, Ichimoku) |
| volume | `{{ row.volume }}` | Volume-based plugins (e.g., MFI, VWAP) |

### Typical Data Flow

```
WatchlistNode           → HistoricalDataNode        → ConditionNode
symbols: [{AAPL}, ...]    symbol: "{{ item }}"         items.from: "{{ item.time_series }}"
                          output: {                     items.extract: { symbol, exchange, date, close }
                            symbol, exchange,            plugin: "RSI"
                            time_series: [               fields: { period: 14, ... }
                              {date, open, high,
                               low, close, volume},
                              ...
                            ]
                          }
```

### ConditionNode Output

The executor returns (not just the `result` port):

| Key | Type | Description |
|-----|------|-------------|
| symbols | symbol_list | Input symbols (normalized) |
| result | boolean | Whether any symbol passed the condition |
| passed_symbols | symbol_list | Symbols meeting the condition |
| failed_symbols | symbol_list | Symbols not meeting the condition |
| symbol_results | array | Detailed per-symbol results with plugin output fields (e.g., rsi, signal) |
| values | array | Full output data per symbol |

---

## 6. Symbol Data Format

**Always use arrays of objects with `symbol` and `exchange` fields.**

Correct:
```json
[
  { "symbol": "AAPL", "exchange": "NASDAQ" },
  { "symbol": "JPM", "exchange": "NYSE" }
]
```

Wrong:
```json
{ "AAPL": { "exchange": "NASDAQ" } }
"AAPL"
["AAPL", "JPM"]
```

### Exchange Codes

**Overseas Stock:**

| Exchange | Market |
|----------|--------|
| NASDAQ | US NASDAQ |
| NYSE | US NYSE |
| AMEX | US AMEX |

**Overseas Futures:**

| Exchange | Market |
|----------|--------|
| CME | Chicago Mercantile Exchange |
| CBOT | Chicago Board of Trade |
| NYMEX | New York Mercantile Exchange |
| COMEX | Commodity Exchange |
| SGX | Singapore Exchange |
| EUREX | Eurex (Europe) |
| HKEX | Hong Kong Exchange |
| OSE | Osaka Exchange (Japan) |
| ICE | Intercontinental Exchange |

> Note: Paper trading (mock) is only supported on HKEX for overseas futures.

**Korea Stock:**

| Exchange | Market |
|----------|--------|
| KRX | Korea Exchange (umbrella) |

Market filter values: `KOSPI`, `KOSDAQ`, `all`

> Note: Korea stock is live trading only (no paper trading mode).

---

## 7. IfNode Branching

IfNode evaluates a condition and routes execution to `true` or `false` branches.

### Configuration

```json
{
  "id": "if_check",
  "type": "IfNode",
  "left": "{{ nodes.account.balance.available }}",
  "operator": ">=",
  "right": 1000000
}
```

### Operators

`==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `contains`, `not_contains`, `is_empty`, `is_not_empty`

### Branch Edges

```json
{ "from": "if_check", "to": "order_node", "from_port": "true" },
{ "from": "if_check", "to": "notify_node", "from_port": "false" }
```

### Output Ports

| Port | Type | Description |
|------|------|-------------|
| true | any | Emitted when condition is true |
| false | any | Emitted when condition is false |
| result | boolean | The boolean evaluation result |

### Cascading Skip

Nodes on the inactive branch (and their downstream chain) are automatically skipped. A downstream node is skipped only when ALL its incoming edges are inactive.

### Important Limitation

IfNode does NOT pass through data. It only outputs a boolean signal. Do not use IfNode to gate array data for auto-iterate. Use SymbolFilterNode or ConditionNode instead.

---

## 8. Broker Connection

Nodes that call LS Securities API (Account, MarketData, Historical, Order, etc.) require a broker connection. This is **automatically injected** through DAG edge traversal.

### Pattern

```json
"nodes": [
  { "id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred" },
  { "id": "account", "type": "OverseasStockAccountNode" }
],
"edges": [
  { "from": "broker", "to": "account" }
]
```

- Only the BrokerNode needs `credential_id`.
- Downstream API nodes receive the connection automatically via edge.
- No `{{ nodes.broker.connection }}` binding needed.

### Product Scope

Each broker type serves specific node types. Do not mix:

| Broker | Compatible Nodes |
|--------|-----------------|
| OverseasStockBrokerNode | OverseasStock* nodes |
| OverseasFuturesBrokerNode | OverseasFutures* nodes |
| KoreaStockBrokerNode | KoreaStock* nodes |

---

## 9. Node Output Ports Reference

### Infra Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| StartNode | start | signal | Workflow start signal |
| ThrottleNode | data | any | Throttled data passthrough |
| SplitNode | item | any | Current split item |
| SplitNode | index | integer | Current index (0-based) |
| SplitNode | total | integer | Total item count |
| AggregateNode | array | array | Collected items array |
| AggregateNode | value | number | Aggregated value |
| AggregateNode | count | integer | Item count |
| IfNode | true | any | Condition true signal |
| IfNode | false | any | Condition false signal |
| IfNode | result | boolean | Boolean result |
| All BrokerNodes | connection | broker_connection | API connection |

### Account Nodes

All account nodes (OverseasStock/OverseasFutures/KoreaStock) share the same ports:

| Port | Type | Description |
|------|------|-------------|
| held_symbols | symbol_list | Held symbol list `[{symbol, exchange}]` |
| balance | balance_data | Deposit, available balance, total equity |
| positions | position_data | Position details `[{symbol, exchange, quantity, avg_price, pnl, pnl_rate, ...}]` |

### Open Orders Nodes

All open orders nodes (OverseasStock/OverseasFutures/KoreaStock) share:

| Port | Type | Description |
|------|------|-------------|
| open_orders | order_list | Pending/open order list |
| count | number | Number of open orders |

### Market Data Nodes

All market data nodes (OverseasStock/OverseasFutures/KoreaStock) share the same port:

| Port | Type | Description |
|------|------|-------------|
| value | market_data | Current price, change, volume, etc. |

### Historical Data Nodes

All historical data nodes share the same ports:

| Port | Type | Description |
|------|------|-------------|
| value | ohlcv_data | Single result: `{symbol, exchange, time_series: [{date, open, high, low, close, volume}, ...]}` |
| values | array | Array of results (compatibility) |
| period | string | Date range string (e.g., `"20260101~20260401"`) |

### Symbol Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| WatchlistNode | symbols | symbol_list | Defined watchlist symbols |
| MarketUniverseNode | symbols | symbol_list | Universe symbols |
| MarketUniverseNode | count | integer | Symbol count |
| ScreenerNode | symbols | symbol_list | Screened symbols |
| ScreenerNode | count | integer | Result count |
| SymbolFilterNode | symbols | symbol_list | Filtered symbols |
| SymbolFilterNode | count | integer | Result count |
| ExclusionListNode | excluded | symbol_list | Excluded symbols |
| ExclusionListNode | filtered | symbol_list | Remaining symbols after exclusion |
| ExclusionListNode | count | integer | Excluded count |
| ExclusionListNode | reasons | object | Per-symbol exclusion reasons |
| SymbolQueryNode (all) | symbols | symbol_list | Query result symbols |
| FundamentalNode (all) | value | fundamental_data | PER, EPS, market cap, etc. |
| CurrencyRateNode | rates | array | Exchange rate data array |
| CurrencyRateNode | krw_rate | number | KRW exchange rate |
| FearGreedIndexNode | value | number | Fear & Greed Index value (0-100) |
| FearGreedIndexNode | label | string | Label (e.g., "Extreme Fear", "Greed") |
| FearGreedIndexNode | previous_close | number | Previous close value |
| FundamentalDataNode | data | array | Fundamental data array |
| FundamentalDataNode | summary | object | Summary statistics |

### Condition & Logic Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| ConditionNode | result | condition_result | Boolean + passed/failed symbols + plugin output |
| LogicNode | result | condition_result | Combined boolean result |
| LogicNode | passed_symbols | symbol_list | Symbols passing logic |

### Order Nodes

All order nodes (New/Modify/Cancel for all markets) share:

| Port | Type | Description |
|------|------|-------------|
| result | order_result | Order execution result |

### Risk Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| PositionSizingNode | order | order | Calculated order with quantity/price |
| PositionSizingNode | quantity | integer | Calculated quantity |
| PortfolioNode | allocated_capital | object | Capital allocation per symbol |
| PortfolioNode | equity_curve | array | Historical equity curve |
| PortfolioNode | performance_metrics | object | Sharpe, MDD, etc. |
| PortfolioNode | rebalance_orders | array | Rebalance order list |
| BacktestEngineNode | equity_curve | portfolio_result | Backtest equity curve |
| BacktestEngineNode | trades | trade_list | Trade history |
| BacktestEngineNode | metrics | performance_summary | Performance metrics (Sharpe, MDD, etc.) |
| BacktestEngineNode | summary | performance_summary | Backtest summary |
| BenchmarkCompareNode | combined_curve | array | Combined equity curves |
| BenchmarkCompareNode | comparison_metrics | array | Per-strategy comparison metrics |
| BenchmarkCompareNode | ranking | array | Strategy ranking |
| BenchmarkCompareNode | strategies_meta | array | Strategy metadata |

### Schedule Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| ScheduleNode | trigger | signal | Cron trigger signal |
| TradingHoursFilterNode | passed | signal | Within trading hours |
| TradingHoursFilterNode | blocked | signal | Outside trading hours |

### Data Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| HTTPRequestNode | response | any | HTTP response body |
| HTTPRequestNode | status_code | number | HTTP status code |
| HTTPRequestNode | success | boolean | Request success flag |
| HTTPRequestNode | error | string | Error message if failed |
| FieldMappingNode | mapped | any | Transformed data |
| SQLiteNode | rows | array | Query result rows |
| SQLiteNode | affected_count | integer | Affected row count |
| SQLiteNode | last_insert_id | integer | Last inserted row ID |
| FileReaderNode | texts | array | Parsed text content per file |
| FileReaderNode | data_list | array | Structured data per file (CSV rows, JSON objects, etc.) |
| FileReaderNode | metadata | array | File metadata (name, size, format, page count, etc.) |

### Display Nodes

All display nodes output:

| Port | Type | Description |
|------|------|-------------|
| rendered | signal | Render completion signal |

### AI Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| LLMModelNode | connection | ai_model | LLM connection for AIAgentNode |
| AIAgentNode | response | any | LLM response (text/json/structured) |
| AIAgentNode | tool_calls | array | Tool call history |
| AIAgentNode | thinking | string | LLM thinking process |

### Messaging Nodes

| Node | Port | Type | Description |
|------|------|------|-------------|
| TelegramNode | sent | signal | Message sent confirmation |
| TelegramNode | message_id | string | Sent message ID |

### Real-time Nodes

Real-time market data nodes (OverseasStock/OverseasFutures/KoreaStock):

| Port | Type | Description |
|------|------|-------------|
| ohlcv_data | ohlcv_data | Real-time OHLCV |
| data | market_data_full | Full tick data |

Real-time account nodes:

| Port | Type | Description |
|------|------|-------------|
| held_symbols | symbol_list | Current held symbols |
| balance | balance_data | Real-time balance |
| positions | position_data | Real-time positions |
| open_orders | order_list | Open orders |

Real-time order event nodes:

| Port | Type | Description |
|------|------|-------------|
| order_event | order_event | Fill/cancel/modify event |

---

## 10. Common Patterns

### Pattern A: Basic Account Query

```
StartNode → BrokerNode → AccountNode
```

### Pattern B: Watchlist + Market Data

```
StartNode → BrokerNode → WatchlistNode → MarketDataNode ({{ item }})
```
Auto-iterate: WatchlistNode outputs symbol array → MarketDataNode runs per symbol.

### Pattern C: Historical + Condition (Plugin)

```
WatchlistNode → HistoricalDataNode ({{ item }}) → ConditionNode (items mapping)
```
Auto-iterate: WatchlistNode → HistoricalDataNode per symbol. ConditionNode uses `items.from`/`items.extract` to process time series.

### Pattern D: Filter Then Act

```
WatchlistNode  ─┐
                 ├→ SymbolFilterNode (difference) → NewOrderNode ({{ item }})
AccountNode    ─┘
```
Filter removes held symbols, then auto-iterate orders for remaining symbols.

### Pattern E: Scheduled Loop

```
StartNode → BrokerNode → ScheduleNode → TradingHoursFilterNode → [strategy nodes]
```
ScheduleNode fires on cron, TradingHoursFilterNode gates by market hours.

### Pattern F: IfNode Branching

```
                                  ┌─(true)──→ OrderNode
AccountNode → IfNode (balance >= X)
                                  └─(false)─→ NotifyNode
```
Use `from_port: "true"` or `from_port: "false"` in edges.

### Pattern G: AI Agent

```
LLMModelNode ──(ai_model edge)──→ AIAgentNode
MarketDataNode ──(tool edge)──→ AIAgentNode
AccountNode ──(tool edge)──→ AIAgentNode
```
LLMModelNode provides LLM connection. Other nodes registered as tools via `tool` edge type.

---

## 11. Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Node ID with hyphens | `rsi-filter` parses as subtraction in `{{ nodes.rsi-filter.result }}` | Use underscores: `rsi_filter` |
| Symbol as string | `"AAPL"` instead of `{symbol, exchange}` | Always use `[{symbol: "AAPL", exchange: "NASDAQ"}]` |
| Missing items mapping | ConditionNode without `items.from`/`items.extract` | Add items mapping when using plugins with HistoricalData |
| IfNode as data gate | Expecting IfNode to pass arrays through | Use SymbolFilterNode or ConditionNode for data filtering |
| Mixing broker types | OverseasStockBrokerNode → KoreaStockAccountNode | Match broker and node product types |
| Manual connection binding | `connection: "{{ nodes.broker.connection }}"` | Just add edge from broker to node (auto-injected) |
| Missing broker in chain | AccountNode without upstream BrokerNode | All API nodes need BrokerNode upstream via edges |
| Order node retry | Default retry on order nodes causes duplicate orders | Order nodes have retry disabled by default (keep it that way) |

---

## 12. Node ID Naming Conventions

- Use lowercase with underscores: `rsi_condition`, `buy_order`, `account_sell`
- Be descriptive: `filter_buy` not `f1`, `if_stop_loss` not `if1`
- Prefix with purpose when using duplicate types: `account_buy`, `account_sell` (two AccountNodes)
- Never use hyphens, spaces, or special characters

---

## 13. HKEX Paper Trading (LS 모의투자)

LS Securities (LS증권) 모의투자는 HKEX 한 거래소만 지원합니다. CME / EUREX 등 다른
거래소는 모의투자 불가 (실거래만 가능). HKEX 미니선물 (Mini Hang Seng / Mini HSCEI) 위주.

### 13.1 핵심 제약

| 제약 | 영향 | 권장 패턴 |
|------|------|-----------|
| 모의투자: **HKEX 한 거래소** | 모든 broker `paper_trading=true` 필수 | broker 노드 `paper_trading: true` |
| **시장가 주문 불가** | 청산도 limit | NewOrderNode `order_type: "limit"` + `price` 명시 |
| 통화: **HKD** | balance / fill 가격 | KRW 환산 시 별도 환율 노드 |
| 거래시간 (KST 기준) | 데이세션 + T+1 야간세션 | 아래 13.2 참조 |

### 13.2 HKEX 거래시간 (KST 환산)

```
데이 1부:  KST 10:15-13:00 (HKT 09:15-12:00)
점심 휴장: KST 13:00-14:00 (HKT 12:00-13:00)
데이 2부:  KST 14:00-17:30 (HKT 13:00-16:30)
저녁 휴장: KST 17:30-18:15 (HKT 16:30-17:15)
T+1 야간:  KST 18:15-04:00(+1) (HKT 17:15-03:00+1)
```

거의 24시간 거래 + 세 휴장 구간. **`TradingHoursFilterNode` 는 현재 단일 윈도우만 지원**
(multi-window / wrap-around 미지원) 이므로, HKEX 세션 표현에 다음 옵션 중 선택:

| 패턴 | 사용 시점 | 예제 |
|------|----------|------|
| 단일 데이 윈도우 `10:15-17:30 KST` | 룰베이스 cron 진입 (점심 휴장 시 cron 자연 skip) | 81, 83, 85 |
| TradingHoursFilter **제거** | realtime 노드 — tick 자체가 휴장 시 안 옴 | 82 (realtime 손절) |
| Schedule 만 (TradingHoursFilter 없음) | 거래 불필요 (백테스트, 리포트) | 84 |
| LogicNode + 3개 TradingHoursFilter OR | 세 세션 모두 정확히 표현 필요 시 | (예제 없음, future work) |

### 13.3 월물 명명 규칙

```
HM[CE] + 월코드 + 연도2자리
  │      │       │
  │      │       └─ 26 = 2026
  │      └─ F=1월, G=2월, H=3월, J=4월, K=5월, M=6월,
  │         N=7월, Q=8월, U=9월, V=10월, X=11월, Z=12월
  └─ HMH = Mini Hang Seng, HMCE = Mini HSCEI
```

**예**: `HMHJ26` = Mini Hang Seng **2026년 4월물**

**틱 가치**: HMH/HMCE 미니선물 모두 약 10 HKD/tick (~1.3 USD).

**Roll-over**: 분기물(H/M/U/Z)이 가장 유동성 풍부. 만기 임박 시 다음 월물로 교체. 자동화는
ExclusionListNode 정적 블랙리스트 (예제 85) 또는 향후 LS 캘린더 연동.

> ⚠️ **예제 월물은 시간이 지나면 만료됩니다.** 만기 경과 월물은 `OverseasFuturesHistoricalDataNode`
> 가 **에러 없이 빈 `time_series`** 를 반환 → 다운스트림 condition/sizing 이 silent 하게 무진입.
> 예제 81-85 는 작성 시점 기준 live 월물(2026 기준 `HMHM26`/`HMCEM26`, 6월물 M)을 사용하며,
> 실행 시점이 만기를 지났다면 `OverseasFuturesSymbolQueryNode` 로 현재 front month 를 확인해
> Watchlist 심볼을 갱신하세요. (2026-05-29 검증: J월물 만료 → M월물 roll-forward)

### 13.4 신규 예제 81-85 (HKEX 풀세트)

| 예제 | 시나리오 | 학습 포인트 |
|------|---------|-----------|
| 81 | 다종목 RSI+Bollinger Logic AND 진입 | auto-iterate + LogicNode 결합 + ATR 사이징 |
| 82 | 실시간 → IfNode 손절 자동매도 | Connection Rule A-2 + ThrottleNode + balance partial-failure |
| 83 | AI Agent 리스크 매니저 일일 리포트 | LLMModelNode + AIAgentNode + Tool 엣지 + structured output |
| 84 | 백테스트 + Schedule 아침 리포트 | BacktestEngineNode + BenchmarkCompareNode + Telegram |
| 85 | 월물 스크리너 + 조건 진입 + roll-over mock | ExclusionListNode + ATR + IfNode is_not_empty 분기 |

기존 HKEX 예제: `39-realtime-futures-tick`, `57-futures-paper-backtest-heavy`,
`61-hkex-futures-bot`, `62-rsi-futures-bot` 도 참조.
