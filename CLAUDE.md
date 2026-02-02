# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProgramGarden is a no-code system trading DSL (Domain Specific Language) platform using LS Securities (LS증권) OpenAPI. It enables investors to automate trading strategies through a node-based workflow system without coding knowledge.

**Language**: Primary development language is Python. Documentation and comments are in Korean. Use Korean when communicating with users unless they prefer English.

## Package Structure

```
src/
├── programgarden/      # Main package (workflow execution engine) - for external users
│   ├── programgarden/  # Core module: executor.py, context.py, resolver.py
│   └── examples/       # Test/demo code for the package
│       └── python_server/  # FastAPI backend server example
├── core/               # programgarden-core: node types, base classes, registry, i18n
│   └── programgarden_core/
│       ├── nodes/      # Node definitions (OverseasStockBrokerNode, ConditionNode, etc.)
│       ├── bases/      # Base classes (BaseExecutionListener, etc.)
│       ├── models/     # Pydantic models (FieldSchema, etc.)
│       ├── registry/   # Node and plugin registries
│       └── i18n/locales/  # Translation files (ko.json, en.json)
├── finance/            # programgarden-finance: LS Securities API wrapper
│   └── programgarden_finance/
└── community/          # programgarden-community: strategy plugins (RSI, MACD, etc.)
    └── programgarden_community/plugins/
```

## Development Commands

Each package uses Poetry for dependency management. Commands must be run from the package directory:

```bash
# Run tests
cd src/core && poetry run pytest tests/
cd src/programgarden && poetry run pytest tests/

# Run a single test
cd src/programgarden && poetry run pytest tests/test_file.py::test_function -v

# Run example server (port 8766)
cd src/programgarden && poetry run python examples/python_server/server.py

# Kill server if port is occupied
lsof -ti:8766 | xargs kill -9
```

## Architecture

### Node-Based DSL

Workflows are defined as JSON with nodes, edges, and credentials:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}"}
  ],
  "edges": [{"from": "broker", "to": "rsi"}],
  "credentials": [
    {
      "id": "broker-cred",
      "type": "broker_ls_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ]
}
```

### Key Concepts

- **Edges**: Define execution order only (node IDs only)
- **Data Binding**: Use `{{ nodes.nodeId.port }}` expressions in node config
- **Auto-Iterate**: When previous node outputs an array, next node auto-executes for each item
- **Broker Connection**: Automatically injected by Executor via DAG traversal. No explicit `connection` binding needed
- **Product Scope**: Each broker/market/account node is split by product type (`overseas_stock` / `overseas_futures`)
- **Plugins**: Referenced via `plugin` field in ConditionNode, NewOrderNode, etc.
- **Credentials**: Referenced by `credential_id`, defined in `credentials` section as a list

### Auto-Iterate Expressions

When a node outputs an array, the next node automatically executes for each item:

```
[AccountNode] → [FieldMappingNode] → [NewOrderNode]
     │               │                    │
     │               └─ Executes 3 times   └─ Executes 3 times
     └─ positions: [{...}, {...}, {...}]     using {{ item }}
```

**Item Keywords:**
| Keyword | Description | Example |
|---------|-------------|---------|
| `item` | Current iteration item | `{{ item.symbol }}` |
| `index` | Current index (0-based) | `{{ index }}` |
| `total` | Total item count | `{{ total }}` |

**Method Chaining:**
```json
"data": "{{ nodes.account.all() }}"
"first": "{{ nodes.account.first() }}"
"filtered": "{{ nodes.account.filter('pnl > 0') }}"
"symbols": "{{ nodes.account.map('symbol') }}"
"total": "{{ nodes.account.sum('quantity') }}"
"avg": "{{ nodes.account.avg('pnl') }}"
```

**Chaining Example:**
```json
"profit_count": "{{ nodes.account.filter('pnl > 0').count() }}"
```

**Function Namespaces:**
| Namespace | Functions | Example |
|-----------|-----------|---------|
| `date` | today(), ago(), later(), months_ago(), year_start(), year_end(), month_start() | `{{ date.ago(30, format='yyyymmdd') }}` |
| `finance` | pct_change(), pct(), discount(), markup(), annualize(), compound() | `{{ finance.pct_change(100, 110) }}` |
| `stats` | mean(), avg(), median(), stdev(), variance() | `{{ stats.mean([1,2,3]) }}` |
| `format` | pct(), currency(), number() | `{{ format.pct(12.34) }}` → "12.34%" |
| `lst` | first(), last(), count(), pluck(), flatten() | `{{ lst.pluck(items, 'name') }}` |

### Node Categories (10, 49 nodes)

| Category | Nodes |
|----------|-------|
| infra | StartNode, ThrottleNode, SplitNode, AggregateNode, OverseasStockBrokerNode, OverseasFuturesBrokerNode |
| account | OverseasStockAccountNode, OverseasFuturesAccountNode, OverseasStockOpenOrdersNode, OverseasFuturesOpenOrdersNode, OverseasStockRealAccountNode, OverseasFuturesRealAccountNode, OverseasStockRealOrderEventNode, OverseasFuturesRealOrderEventNode |
| market | OverseasStockMarketDataNode, OverseasFuturesMarketDataNode, OverseasStockRealMarketDataNode, OverseasFuturesRealMarketDataNode, OverseasStockHistoricalDataNode, OverseasFuturesHistoricalDataNode, OverseasStockSymbolQueryNode, OverseasFuturesSymbolQueryNode, WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode |
| condition | ConditionNode, LogicNode |
| order | OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode, OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode, PositionSizingNode |
| risk | PortfolioNode |
| schedule | ScheduleNode, TradingHoursFilterNode |
| data | SQLiteNode, HTTPRequestNode, FieldMappingNode |
| display | TableDisplayNode, LineChartNode, MultiLineChartNode, CandlestickChartNode, BarChartNode, SummaryDisplayNode |
| analysis | BacktestEngineNode, BenchmarkCompareNode |

### ExecutionListener Callbacks

| Callback | Description |
|----------|-------------|
| `on_node_state_change` | Node state change (pending/running/completed/failed) |
| `on_edge_state_change` | Edge state change |
| `on_log` | Log events |
| `on_job_state_change` | Job state change |
| `on_display_data` | Display data |
| `on_workflow_pnl_update` | Real-time workflow/account P&L (FIFO-based, auto-detected) |
| `on_retry` | Node retry event (attempt count, error type, next retry delay) |

### Resilience (Retry/Fallback)

외부 API 호출 노드에서 `resilience` 필드로 재시도 및 실패 처리 설정:

```python
class MyAPINode(BaseMessagingNode):
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.SKIP),
        )
    )
```

| 설정 | 설명 | 기본값 |
|------|------|--------|
| `retry.enabled` | 재시도 활성화 | False |
| `retry.max_retries` | 최대 재시도 횟수 (1-10) | 3 |
| `retry.base_delay` | 재시도 대기 시간 (초) | 1.0 |
| `retry.exponential_backoff` | 지수 백오프 | True |
| `fallback.mode` | 실패 시 동작 (error/skip/default_value) | error |
| `fallback.default_value` | 기본값 (mode=default_value일 때) | None |

**주문 노드 주의:** 주문 노드는 중복 주문 위험으로 기본적으로 재시도 비활성화됨.

## Node Development

### Adding/Modifying Nodes

Node definitions are in `src/core/programgarden_core/nodes/`. Each node uses:
- Pydantic model for configuration
- `FieldSchema` for field metadata (type, expression_mode, category)
- `config_schema` for UI configuration

Key files:
- `src/core/programgarden_core/models/field_binding.py` - FieldSchema, UIComponent, ExpressionMode
- `src/core/programgarden_core/registry/node_registry.py` - Node registration
- `.github/schemas/NODE_TEMPLATE.md` - Complete node schema reference

### i18n

Translation files: `src/core/programgarden_core/i18n/locales/{ko,en}.json`

Key prefixes:
- `nodes.{NodeType}.name/description` - Node name/description
- `fields.{NodeType}.{fieldName}` - Input field descriptions
- `outputs.{NodeType}.{fieldName}` - Output field descriptions

### Symbol Data Format (Required)

Always use arrays with `symbol` and `exchange` fields, never use symbol as dictionary key:

```python
# Correct
[{"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5}]

# Wrong - Don't use symbol as key
{"AAPL": {"rsi": 28.5}}
```

## Custom Slash Commands

Available through `.claude/commands/`:
- `/pg-plan` - Create optimization plan
- `/pg-catch` - Git context recovery after `/clear`
- `/pg-commit` - Detailed git commit with comprehensive message
- `/pg-node` - Add/modify nodes
- `/pg-node-validate` - Validate node schema
- `/pg-node-list` - List registered nodes
- `/pg-integration-test` - Test server integration (python_server)

### Context Recovery (컨텍스트 복구)

`/clear` 후 또는 새 세션에서 이전 작업을 이어가야 할 때, 사용자가 다음과 같이 요청하면 `/pg-catch` 스킬을 실행하세요:
- "이전 작업 이어서", "컨텍스트 복구", "맥락 복구"
- "아까 하던 거 계속", "어디까지 했지?"
- "Phase N 진행해줘", "다음 Phase"

`/pg-catch`는 git 커밋 메시지를 분석하여 브랜치의 작업 목적, 진행 상황, 다음 작업을 파악합니다.

## Testing

### Integration Testing

The `examples/` folder contains integration test code:
- `python_server/` - FastAPI server for workflow execution

### Running Server

```bash
cd src/programgarden && poetry run python examples/python_server/server.py
```
