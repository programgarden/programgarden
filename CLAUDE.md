# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProgramGarden is a no-code system trading DSL (Domain Specific Language) platform using LS Securities (LS증권) OpenAPI. It enables investors to automate trading strategies through a node-based workflow system without coding knowledge.

**Language**: Primary development language is Python. Documentation and comments are in Korean. Use Korean when communicating with users unless they prefer English.

## CRITICAL Rules (반드시 준수)

1. **커밋 메시지에 `Co-Authored-By` 절대 금지**: Git 커밋 시 `Co-Authored-By: Claude ...` 또는 어떤 형태의 Co-Authored-By 라인도 포함하지 마세요. 이 규칙은 예외 없이 모든 커밋에 적용됩니다.

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

### Dynamic Node Injection (동적 노드 주입)

외부 사용자가 community 패키지 기여 없이 런타임에 커스텀 노드를 주입하여 워크플로우에서 사용할 수 있습니다.

**네이밍 규칙**: 동적 노드는 반드시 `Custom_` prefix 사용 (예: `Custom_MyRSI`)

**사용 흐름**:
```python
from programgarden import WorkflowExecutor
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort

# 1. 커스텀 노드 클래스 정의
class CustomRSINode(BaseNode):
    type: str = "Custom_RSI"
    category: NodeCategory = NodeCategory.CONDITION
    period: int = 14

    _outputs = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    async def execute(self, context):
        return {"rsi": 35.5, "signal": "oversold"}

# 2. Executor 생성 및 스키마 등록
executor = WorkflowExecutor()
executor.register_dynamic_schemas([{
    "node_type": "Custom_RSI",
    "category": "condition",
    "outputs": [
        {"name": "rsi", "type": "number"},
        {"name": "signal", "type": "string"},
    ],
}])

# 3. 필요한 타입 확인 및 클래스 주입
required = executor.get_required_custom_types(workflow)  # ["Custom_RSI"]
executor.inject_node_classes({"Custom_RSI": CustomRSINode})

# 4. 워크플로우 실행
job = await executor.execute(workflow)

# 5. 메모리 정리 (선택)
executor.clear_injected_classes()
```

**제약 사항**:
- 동적 노드에서 `credential_id` 사용 불가 (보안상 credential 접근 차단)
- 클래스는 `BaseNode` 상속 필수
- `execute()` 메서드 구현 필수
- 스키마의 output 포트가 클래스에도 정의되어야 함

**API**:
| 메서드 | 설명 |
|--------|------|
| `register_dynamic_schemas(schemas)` | 스키마 등록 (UI 표시용) |
| `get_required_custom_types(workflow)` | 워크플로우에 필요한 커스텀 타입 목록 |
| `inject_node_classes(classes)` | 노드 클래스 주입 |
| `is_dynamic_node_ready(type)` | 실행 준비 완료 여부 확인 |
| `clear_injected_classes()` | 주입된 클래스 초기화 |

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
- `/pg-release` - Update package versions and CHANGELOG
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
