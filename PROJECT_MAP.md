# PROJECT_MAP
@generated: 2026-03-09T00:00:00
@updated: 2026-05-13T01:00:00
@type: python-monorepo
@stack: Python 3.12 | Poetry | Pydantic 2 | asyncio | WebSocket

## TREE
src/
  core/ [72 .py] — programgarden-core 1.12.2
    programgarden_core/
      nodes/ [38 .py] — 73 node classes (12 categories)
      models/ [12 .py] — edge, workflow, credential, resilience, connection_rule, event, exchange, job, plugin_resource, resource
      registry/ [5 .py] — node, plugin, credential, dynamic_node
      bases/ [8 .py] — listener, client, components, mixins, products, sql, storage
      expression/ [2 .py] — template evaluator ({{ nodes.x.y }})
      i18n/ [2 .py + 2 .json] — translator, ko.json, en.json
      presets/ [1 .py + 4 .json] — AI agent presets
  programgarden/ [30 .py] — programgarden 1.21.4
    programgarden/
      executor.py — WorkflowExecutor, NodeExecutors, WorkflowJob
      context.py — ExecutionContext, state, events
      resolver.py — DAG resolver, expression binding
      node_runner.py — standalone node execution
      binding_validator.py — type validation (list[dict], position_data)
      client.py — ProgramGarden.run() facade
      database/ [5 .py] — checkpoint, position_tracker, risk_tracker, query_builder
      providers/ [3 .py] — LLM provider (litellm), errors
      tools/ [7 .py] — registry, sqlite, job, credential, event, definition tools
    examples/workflows/ [80 .json + 80 .md + 00-workflow-guide.md] — runnable workflow demos (incl. 59 trend-trailing, 60 bollinger-reversion, 61 hkex-futures, 68-77 telegram-beginner, 78-80 screener multi-market)
    examples/dynamic_plugins/ [11 .py] — user-contributed simple_* plugin examples
    examples/dynamic_nodes/ [1 .py] — Dynamic_* node definition example
    examples/programmer_example/ [3 .py] — live integration scripts (AI agent, quant)
  finance/ [383 .py] — programgarden-finance 1.6.5 (AI metadata coverage 100% on 150 TR blocks.py)
    programgarden_finance/
      ls/ — LS Securities API wrapper
        overseas_stock/ — REST 17 TR + Real 7 TR + extension (tracker)
        overseas_futureoption/ — REST 28 TR + Real 7 TR + extension (tracker)
        korea_stock/ — REST 75 TR + Real 13 TR + extension (tracker)
        common/ — Real 1 TR (JIF market status, broker-agnostic)
        oauth/ — token management (generate/revoke)
        real_base.py — WebSocket singleton, subscription, reconnect
        config.py — API URLs, rate limits
  community/ [89 .py] — programgarden-community 1.13.2
    programgarden_community/
      plugins/ [78 dirs] — 77 strategy plugins (TECHNICAL 59, POSITION 18)
      nodes/ — 4 community nodes
        messaging/telegram.py — TelegramNode
        market/fear_greed.py — FearGreedIndexNode
        market/fmp.py — FundamentalDataNode
        data/file_reader.py — FileReaderNode (+ _parsers.py)
      nodes_registry.py — community node registration

## PACKAGES
programgarden-core → Node type definitions, models, registry, i18n, expression engine | path:src/core | key:nodes/base.py
programgarden → Workflow execution engine (DAG executor, context, resolver, NodeRunner) | path:src/programgarden | key:executor.py
programgarden-finance → LS Securities OpenAPI wrapper (REST+WebSocket, 3 products) | path:src/finance | key:ls/real_base.py
programgarden-community → Strategy plugins (77) + community nodes (4) | path:src/community | key:plugins/__init__.py

## KEY_FILES
src/core/programgarden_core/nodes/base.py → BaseNode, ProductScope, NodeCategory, OutputPort, POSITION_FIELDS
src/core/programgarden_core/nodes/order.py → BaseOrderNode, order nodes (stock/futures/korea)
src/core/programgarden_core/nodes/ai.py → LLMModelNode, AIAgentNode
src/core/programgarden_core/nodes/condition.py → ConditionNode (positions: list[dict])
src/core/programgarden_core/models/field_binding.py → FieldSchema, UIComponent, ExpressionMode
src/core/programgarden_core/models/workflow.py → WorkflowDefinition, StickyNote
src/core/programgarden_core/registry/node_registry.py → NodeTypeRegistry, NodeTypeSchema
src/core/programgarden_core/bases/listener.py → ExecutionListener protocol, all event types
src/core/programgarden_core/i18n/locales/ko.json → Korean translations (~1000 keys)
src/programgarden/programgarden/executor.py → WorkflowExecutor, all NodeExecutors, WorkflowJob
src/programgarden/programgarden/context.py → ExecutionContext, state management, event emission
src/programgarden/programgarden/resolver.py → WorkflowResolver, DAG sort, expression binding
src/programgarden/programgarden/node_runner.py → NodeRunner for standalone node execution
src/programgarden/programgarden/binding_validator.py → type validator (position_data: list[dict])
src/programgarden/programgarden/database/workflow_risk_tracker.py → WorkflowRiskTracker (HWM, window, events, state)
src/programgarden/programgarden/database/checkpoint_manager.py → CheckpointManager (graceful restart)
src/finance/programgarden_finance/ls/real_base.py → WebSocket singleton, ref_count, auto-resubscribe
src/finance/programgarden_finance/ls/overseas_stock/extension/tracker.py → StockAccountTracker (FIFO PnL)
src/finance/programgarden_finance/ls/korea_stock/extension/tracker.py → KrStockAccountTracker (FIFO PnL)
src/community/programgarden_community/plugins/__init__.py → 77 plugin registrations

## PATTERNS
- Node-based DSL: Pydantic BaseNode subclasses with typed input/output ports
- DAG Workflow Execution: topological sort + auto-iterate array expansion
- Template Expression: {{ nodes.id.port }} binding with method chaining (filter, map, sum)
- Plugin Registry: NodeTypeRegistry + PluginRegistry for extensibility
- WebSocket Singleton: ref_count based Real instance sharing per token_manager
- Retry/Fallback Resilience: ResilienceConfig with exponential backoff on external API nodes
- Feature-gated Risk Tracker: opt-in risk features (hwm, window, events, state)
- Connection Rules: realtime→order/AI direct link prevention (ERROR/WARNING)
- Rate Limit Guard: per-node min_interval_sec + max_concurrent enforcement
- Graceful Restart: checkpoint save/restore for workflow recovery
- FIFO PnL Tracking: per-product position tracking with WorkflowPnLEvent
- AI Agent Tool System: existing nodes as LLM function-calling tools via tool edges
- Dynamic Node Injection: runtime Dynamic_ prefixed node class injection
- List-based Collections: symbol_list, order_list, ohlcv_data, position_data all use list[dict]
- i18n: ko/en translations for all node fields, ports, enums
- Poetry Monorepo: 4 packages with path-based develop dependencies

## DEPS
### programgarden-core 1.12.2
pydantic>=2.0.0

### programgarden 1.21.4
pydantic>=2.0.0 | croniter^6.0.0 | aiohttp^3.9.0 | aiosqlite^0.20.0
litellm>=1.40.0 | yfinance^0.2.0 | psutil^6.0.0
python-dotenv^1.1.0 | pytickersymbols>=1.17.5 | lxml^6.0.2
dev: fastapi^0.128.0 | uvicorn^0.40.0 | pytest^8.0.0

### programgarden-finance 1.6.3
pydantic>=2.11.7 | requests^2.32.4 | aiohttp^3.10.0 | websockets^15.0.1
redis^6.4.0 | python-dotenv^1.1.1

### programgarden-community 1.13.2
pypdf>=4.0.0
extras: python-docx (docx) | openpyxl (xlsx) | pdfplumber (pdf-tables)

## STATE
- [x] Overseas Stock Nodes: 22 nodes (broker, account, market, order, realtime, symbol)
- [x] Overseas Futures Nodes: 22 nodes (same structure as stock)
- [x] Korea Stock Nodes: 13 nodes (broker, account, market, order, realtime, symbol)
- [x] Korea Stock Finance API: 75 REST + 13 Real TR with KrStockAccountTracker
- [x] Finance TR AI Metadata: 150/150 blocks.py with Field(title/description/examples) — chatbot-ready model_json_schema()
- [x] Korea Stock Market TR 11: t1302/t1486/t1305/t1488/t1449/t1427/t1104/t1105/t1310/t1308/t1410 series — partial-evidence sign enum policy on t1410 (LS undocumented, sibling convention + live row evidence)
- [x] AI Agent: LLMModelNode + AIAgentNode with tool edges (all connected tools forwarded to LLM)
- [x] Strategy Plugins: 77 plugins (TECHNICAL 59 + POSITION 18)
- [x] Community Nodes: TelegramNode, FearGreedIndexNode, FundamentalDataNode, FileReaderNode
- [x] IfNode: conditional branching with cascading skip
- [x] Graceful Restart: checkpoint save/restore with 10-min expiry
- [x] WorkflowRiskTracker: feature-gated HWM/window/events/state
- [x] Financial Safety Audit: 47 fixes (CRITICAL 8 + HIGH 21 + MEDIUM 14 + LOW 7)
- [x] Connection Rules + Rate Limit Guard: realtime→order protection
- [x] WebSocket Singleton: ref_count based session sharing
- [x] NodeRunner: standalone node execution API
- [x] Dynamic Node Injection: Dynamic_ prefix runtime nodes
- [x] FIFO PnL: overseas stock/futures/korea stock tracking
- [x] DeepSeek LLM: provider support added
- [x] on_notification callback: investor notification channel (8 categories, 3 severities)
- [x] Plugin output_fields: schema documents plugin-specific output fields
- [x] FileReaderNode: 7 formats (PDF/TXT/CSV/JSON/MD/DOCX/XLSX) + pdfplumber tables
- [x] position_data list[dict] unify: overseas futures producer + 10 consumer plugins aligned
- [x] Example bots (consolidated into examples/workflows/): 59 trend-trailing, 60 bollinger-reversion, 61 hkex-futures
- [x] Node AI metadata: 5 ClassVars (_usage / _features / _anti_patterns / _examples / _node_guide) on all 73 nodes
- [x] MarketStatusNode: JIF-based real-time market status (12 markets, broker-agnostic, AI-Tool enabled)
- [x] get_state() diagnostic payload (1.21.5): per-node state cache via internal listener, stats.last_error setter, structured errors[] field with timestamp sort + (node_id) dedup
- [x] Structured validation (core 1.12.3 / programgarden 1.21.10): ValidationResult v2 with ErrorCode (29 codes) / ErrorLocation / Recommendation (9 rules, 8 static + 1 runtime) / ValidationLimits (capping) / ResultSummary (cascade-aware next_action_hint). Cascade suppression for UNKNOWN_NODE_TYPE / MISSING_REQUIRED_BROKER / CYCLE_DETECTED / DUPLICATE_NODE_ID. WorkflowJob.get_structured_errors() for dry_run runtime captures.
- [x] ScreenerNode multi-market routing: `market` field (auto / overseas_stock / overseas_futures / korea_stock) + broker auto-detect via find_parent_output + LS overseas_stock fast path + yfinance fallback for futures/korea_stock + visible_when-based field hiding + universe-fallback guard. Example workflows 78-80 cover the trio.

## CONVENTIONS
- language: Python 3.12+, docs/comments in Korean, code in English
- commit: feat/fix/docs/release/chore/refactor/test prefix, detailed body in Korean
- branch: feat/, fix/, modify/, release/ prefix
- testing: pytest + pytest-asyncio, per-package test dirs
- node naming: {Product}{Function}Node (e.g., OverseasStockMarketDataNode)
- plugin naming: snake_case folder, register in plugins/__init__.py
- i18n keys: nodes.{Type}.name, fields.{Type}.{field}, outputs.{Type}.{port}
- credential: credential_id reference, data as List[CredentialDataItem]
- symbol format: [{symbol, exchange, ...}] array, never use symbol as dict key
- position_data: list[dict] with "symbol" key (never dict keyed by symbol)
- expression: {{ nodes.nodeId.port }} with nodes. prefix
- no Co-Authored-By: git commits must not include Co-Authored-By lines
