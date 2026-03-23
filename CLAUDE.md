# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProgramGarden is a no-code system trading DSL (Domain Specific Language) platform using LS Securities (LS증권) OpenAPI. It enables investors to automate trading strategies through a node-based workflow system without coding knowledge.

**Language**: Primary development language is Python. Documentation and comments are in Korean. Use Korean when communicating with users unless they prefer English.

## Project Map

프로젝트 전체 구조는 [PROJECT_MAP.md](PROJECT_MAP.md) 참조. `/pg-read-map`으로 로드 가능.

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
└── community/          # programgarden-community: 67 strategy plugins + 3 community nodes
    └── programgarden_community/
        ├── plugins/    # 67 strategy plugins (RSI, MACD, Ichimoku, ZScore, PairTrading, TurtleBreakout, MagicFormula, SupportResistanceLevels, LevelTouch, etc.)
        └── nodes/      # Community nodes (TelegramNode, FearGreedIndexNode, FundamentalDataNode, FileReaderNode)
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

Workflows are defined as JSON with nodes, edges, credentials, and notes:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}"}
  ],
  "edges": [{"from": "broker", "to": "rsi"}],
  "credentials": [
    {
      "credential_id": "broker-cred",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ],
  "notes": [
    {"id": "note-1", "content": "## RSI 전략 메모", "color": 1, "width": 300, "height": 200, "position": {"x": 100, "y": 50}}
  ]
}
```

### Key Concepts

- **Edges**: Define execution order and connection type. Types: `main` (DAG execution, default), `ai_model` (LLM connection), `tool` (AI Agent tool registration). Optional `from_port` field for conditional branching (e.g., IfNode's `true`/`false` ports). Supports dot notation: `"from": "if1.true"`
- **Data Binding**: Use `{{ nodes.nodeId.port }}` expressions in node config
- **Auto-Iterate**: When previous node outputs an array, next node auto-executes for each item
- **Broker Connection**: Automatically injected by Executor via DAG traversal. No explicit `connection` binding needed
- **Product Scope**: Each broker/market/account node is split by product type (`overseas_stock` / `overseas_futures`)
- **Plugins**: Referenced via `plugin` field in ConditionNode, NewOrderNode, etc.
- **Credentials**: Referenced by `credential_id`, defined in `credentials` section as a list
- **Notes (Sticky Notes)**: Canvas annotations for documentation. Not executed. `content` supports Markdown, `color` (0-7), `width/height` (px), `position` (x, y)

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

### Node Categories (12, 72 nodes)

| Category | Nodes |
|----------|-------|
| infra | StartNode, ThrottleNode, SplitNode, AggregateNode, IfNode, OverseasStockBrokerNode, OverseasFuturesBrokerNode, KoreaStockBrokerNode |
| account | OverseasStockAccountNode, OverseasFuturesAccountNode, OverseasStockOpenOrdersNode, OverseasFuturesOpenOrdersNode, OverseasStockRealAccountNode, OverseasFuturesRealAccountNode, OverseasStockRealOrderEventNode, OverseasFuturesRealOrderEventNode, KoreaStockAccountNode, KoreaStockOpenOrdersNode, KoreaStockRealAccountNode, KoreaStockRealOrderEventNode |
| market | OverseasStockMarketDataNode, OverseasStockFundamentalNode, OverseasFuturesMarketDataNode, OverseasStockRealMarketDataNode, OverseasFuturesRealMarketDataNode, OverseasStockHistoricalDataNode, OverseasFuturesHistoricalDataNode, OverseasStockSymbolQueryNode, OverseasFuturesSymbolQueryNode, WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, ExclusionListNode, CurrencyRateNode, FearGreedIndexNode, FundamentalDataNode, KoreaStockMarketDataNode, KoreaStockFundamentalNode, KoreaStockHistoricalDataNode, KoreaStockSymbolQueryNode, KoreaStockRealMarketDataNode |
| condition | ConditionNode, LogicNode |
| order | OverseasStockNewOrderNode, OverseasStockModifyOrderNode, OverseasStockCancelOrderNode, OverseasFuturesNewOrderNode, OverseasFuturesModifyOrderNode, OverseasFuturesCancelOrderNode, PositionSizingNode, KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode |
| risk | PortfolioNode |
| schedule | ScheduleNode, TradingHoursFilterNode |
| data | SQLiteNode, HTTPRequestNode, FieldMappingNode, FileReaderNode |
| display | TableDisplayNode, LineChartNode, MultiLineChartNode, CandlestickChartNode, BarChartNode, SummaryDisplayNode |
| analysis | BacktestEngineNode, BenchmarkCompareNode |
| ai | LLMModelNode, AIAgentNode |
| messaging | TelegramNode |

### ExecutionListener Callbacks

| Callback | Description |
|----------|-------------|
| `on_node_state_change` | Node state change (pending/running/completed/failed) |
| `on_edge_state_change` | Edge state change |
| `on_log` | Log events |
| `on_job_state_change` | Job state change (running/cycle_completed/completed/failed/cancelled) |
| `on_display_data` | Display data |
| `on_workflow_pnl_update` | Real-time workflow/account P&L (FIFO-based, auto-detected) |
| `on_retry` | Node retry event (attempt count, error type, next retry delay) |
| `on_token_usage` | AI Agent token usage (total_tokens, cost_usd) |
| `on_ai_tool_call` | AI Agent tool call (tool_name, duration_ms) |
| `on_llm_stream` | AI Agent streaming chunk (is_final) |
| `on_risk_event` | Risk threshold breach (drawdown alert, trailing stop trigger) |
| `on_notification` | Investor notification (signal, risk, workflow state, schedule, retry exhausted) |

### Risk Tracker (WorkflowRiskTracker)

노드/플러그인이 `_risk_features`를 선언하면 자동으로 활성화되는 위험관리 데이터 인프라:

- **Opt-in**: 워크플로우에 관련 노드/플러그인이 없으면 `context.risk_tracker = None`
- **Feature-gated**: 선언된 feature만 활성화 (`hwm`, `window`, `events`, `state`)
- **2-Layer**: 인메모리 Hot Layer (틱 처리) + SQLite Cold Layer (30초 flush)
- **기존 DB 공유**: `{workflow_id}_workflow.db`에 테이블만 추가

```python
# 노드에서 선언
class PortfolioNode(BaseNode):
    _risk_features: ClassVar[Set[str]] = {"hwm", "window"}

# 플러그인에서 선언 (모듈 레벨)
risk_features: Set[str] = {"hwm"}

# 플러그인에서 사용
async def my_condition(data, fields, context=None, **kwargs):
    if context and context.risk_tracker:
        hwm = context.risk_tracker.get_hwm("AAPL")
```

| Feature | 테이블 | Hot Layer | 용도 |
|---------|--------|-----------|------|
| `hwm` | `risk_high_water_mark` | `Dict[str, HWMState]` | HWM/drawdown 추적 |
| `window` | (없음) | `deque(maxlen=300)` | 변동성/MDD 계산 |
| `events` | `risk_events` | (없음) | 위험 이벤트 감사 이력 |
| `state` | `strategy_state` | (없음) | 전략 상태 KV 저장소 |

### IfNode (Conditional Branch)

워크플로우 DAG에서 조건에 따라 실행 흐름을 if/else 분기하는 범용 노드:

- **카테고리**: infra (SplitNode/AggregateNode과 동일한 흐름 제어)
- **비교 연산자**: `==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `contains`, `not_contains`, `is_empty`, `is_not_empty`
- **출력 포트**: `true` (조건 참), `false` (조건 거짓), `result` (boolean)
- **분기 라우팅**: Edge의 `from_port` 필드 또는 dot notation (`"from": "if1.true"`)
- **캐스케이딩 스킵**: 비활성 브랜치의 하위 노드 체인 전체 자동 스킵
- **합류 처리**: 모든 incoming edge가 비활성일 때만 스킵 (다른 활성 경로 있으면 실행)

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {"id": "if-balance", "type": "IfNode", "left": "{{ nodes.account.balance }}", "operator": ">=", "right": 1000000},
    {"id": "order", "type": "OverseasStockNewOrderNode"},
    {"id": "notify", "type": "TableDisplayNode"}
  ],
  "edges": [
    {"from": "start", "to": "if-balance"},
    {"from": "if-balance", "to": "order", "from_port": "true"},
    {"from": "if-balance", "to": "notify", "from_port": "false"}
  ]
}
```

### AI Agent Node

LLMModelNode + AIAgentNode로 워크플로우에 LLM 기반 분석/의사결정 통합:

- **LLMModelNode**: BrokerNode 패턴과 동일. credential로 LLM API 연결, `ai_model` 엣지로 AIAgentNode에 전파
- **AIAgentNode**: `tool` 엣지로 기존 노드를 Tool로 활용하는 범용 에이전트
- **엣지 타입**: `main` (DAG 실행), `ai_model` (LLM 연결), `tool` (도구 등록)
- **출력 형식**: text, json, structured (output_schema 기반 Pydantic 검증)
- **프리셋**: risk_manager, technical_analyst, news_analyst, strategist
- **도구 선택**: `tool_selection` — `semantic` (FastEmbed 벡터 유사도, 기본값), `all` (전체 전달). 도구 6개 이상 시 자동 선별
- **실시간 보호**: cooldown_sec (기본 60초), ThrottleNode 없이 직접 실시간 노드 연결 차단
- **Stateless**: 매 실행마다 독립 (대화 기억 없음, 현재 데이터를 Tool로 직접 조회)

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

외부 사용자가 community 패키지 기여 없이 런타임에 동적 노드를 주입하여 워크플로우에서 사용할 수 있습니다.

**네이밍 규칙**: 동적 노드는 반드시 `Dynamic_` prefix 사용 (예: `Dynamic_MyRSI`)

**사용 흐름**:
```python
from programgarden import WorkflowExecutor
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort

# 1. 동적 노드 클래스 정의
class DynamicRSINode(BaseNode):
    type: str = "Dynamic_RSI"
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
    "node_type": "Dynamic_RSI",
    "category": "condition",
    "outputs": [
        {"name": "rsi", "type": "number"},
        {"name": "signal", "type": "string"},
    ],
}])

# 3. 필요한 타입 확인 및 클래스 주입
required = executor.get_required_dynamic_types(workflow)  # ["Dynamic_RSI"]
executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

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
| `get_required_dynamic_types(workflow)` | 워크플로우에 필요한 동적 노드 타입 목록 |
| `inject_node_classes(classes)` | 노드 클래스 주입 |
| `is_dynamic_node_ready(type)` | 실행 준비 완료 여부 확인 |
| `clear_injected_classes()` | 주입된 클래스 초기화 |

### NodeRunner (Standalone Node Execution)

워크플로우 없이 개별 노드를 단독 실행하는 경량 러너:

```python
from programgarden import NodeRunner

# 단순 노드
runner = NodeRunner()
result = await runner.run("HTTPRequestNode", url="https://api.example.com", method="GET")

# 브로커 의존 노드 (자동 로그인 + connection 주입)
async with NodeRunner(credentials=[
    {"credential_id": "broker", "type": "broker_ls_overseas_stock",
     "data": {"appkey": "xxx", "appsecret": "yyy"}}
]) as runner:
    result = await runner.run("OverseasStockMarketDataNode",
        credential_id="broker",
        symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        fields=["price", "volume"]
    )
```

**노드 유형별 사용법**:
| 유형 | 예시 | credential 필요 |
|------|------|:---:|
| 단순 | HTTPRequestNode, FieldMappingNode | X |
| Credential | TelegramNode, SlackNode | O (data에 직접 전달) |
| 브로커 의존 | MarketDataNode, AccountNode, OrderNode | O (broker_ls_* type) |

**제한 사항**:
- 실시간(WebSocket) 노드는 미지원 (RealMarketData, RealAccount 등)
- BrokerNode 직접 실행 불필요 (credential 전달 시 자동 처리)
- `raise_on_error=True` 기본값 (에러 시 RuntimeError 발생)

**API**:
| 메서드 | 설명 |
|--------|------|
| `run(node_type, **config)` | 노드 단독 실행 |
| `list_node_types()` | 사용 가능한 노드 타입 목록 |
| `get_node_schema(node_type)` | 노드 스키마 조회 |
| `cleanup()` | 리소스 정리 (LS 세션 등) |

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
- `/pg-test` - 실전 통합 테스트 (단위 + API + 워크플로우 JSON)
- `/pg-release` - TestPyPI 단계별 배포
- `/pg-publish` - 실제 PyPI 프로덕션 배포
- `/pg-update-docs` - Sync documentation with codebase

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
