---
category: ai_agent
tags: [preset, output, text, json, structured, risk_manager, news_analyst, technical_analyst, strategist, output_schema]
priority: high
---

# AI Agent Presets and Output Formats

## Preset System

Presets are pre-defined JSON templates for AIAgentNode roles (personas). When a preset is selected, `system_prompt`, `output_schema`, and `default_config` are automatically populated.

### Preset Application Priority

```
User settings > Preset defaults
```

- **system_prompt**: User prompt is merged after the preset prompt
- **output_schema**: Preset schema is applied if not set by user
- **default_config**: Preset defaults are applied if not set by user

Values explicitly set by the user are always preserved.

### Preset Selection

```json
{
  "id": "agent",
  "type": "AIAgentNode",
  "preset": "risk_manager",
  "user_prompt": "Evaluate the risk of current positions."
}
```

Setting `preset` to `"custom"` or omitting it applies only user settings without a preset.

## 4 Built-in Presets

### 1. risk_manager (Risk Manager)

A conservative risk management expert. Prioritizes loss avoidance above all.

**Role**:
- Evaluate risk of current positions
- Calculate maximum allowed position size per symbol
- Set and monitor stop-loss prices per symbol
- Warn against excessive concentration

**Default Settings**:
| Item | Value |
|------|-------|
| output_format | structured |
| max_tool_calls | 5 |

**output_schema**:
```json
{
  "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Overall portfolio risk level"},
  "positions": {"type": "array", "description": "Per-symbol risk analysis (each item: symbol, risk_level, max_position_size, stop_loss_price)"},
  "reasoning": {"type": "string", "description": "Basis for risk analysis"}
}
```

**Recommended Tool Nodes**: `OverseasStockAccountNode`, `OverseasFuturesAccountNode`, `OverseasStockMarketDataNode`, `OverseasFuturesMarketDataNode`

**Workflow Example**:
```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o", "temperature": 0.2},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "AAPL", "exchange": "NASDAQ"},
    {"id": "agent", "type": "AIAgentNode",
     "preset": "risk_manager",
     "user_prompt": "Evaluate the risk of current positions and suggest stop-loss prices."}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "account", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"}
  ]
}
```

### 2. technical_analyst (Technical Analyst)

An expert who analyzes charts and technical indicators. Makes decisions based on indicators like RSI, MACD, etc.

**Role**:
- Analyze chart patterns and technical indicators
- Interpret signals from RSI, MACD, Bollinger Bands, etc.
- Identify support/resistance levels, determine trends
- Suggest trade timing

**Default Settings**:
| Item | Value |
|------|-------|
| output_format | structured |
| max_tool_calls | 8 |

**output_schema**:
```json
{
  "signal": {"type": "string", "enum": ["strong_buy", "buy", "hold", "sell", "strong_sell"], "description": "Trading signal"},
  "confidence": {"type": "number", "description": "Confidence level (0.0 ~ 1.0)"},
  "support_price": {"type": "number", "description": "Support level price"},
  "resistance_price": {"type": "number", "description": "Resistance level price"},
  "reasoning": {"type": "string", "description": "Basis for technical analysis"}
}
```

**Recommended Tool Nodes**: `OverseasStockHistoricalDataNode`, `OverseasFuturesHistoricalDataNode`, `ConditionNode`, `OverseasStockMarketDataNode`

**Workflow Example**:
```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o", "temperature": 0.3},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "symbol": "AAPL", "exchange": "NASDAQ",
     "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "rsi_check", "type": "ConditionNode", "plugin": "RSI",
     "items": {"from": "{{ nodes.history.value.time_series }}", "extract": {"symbol": "{{ nodes.history.value.symbol }}", "exchange": "{{ nodes.history.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
     "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "agent", "type": "AIAgentNode",
     "preset": "technical_analyst",
     "user_prompt": "Perform a technical analysis of AAPL and provide a trading signal."}
  ],
  "edges": [
    {"from": "broker", "to": "history"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "rsi_check", "to": "agent", "type": "tool"}
  ]
}
```

### 3. news_analyst (News Analyst)

An expert who analyzes market news and events. Evaluates sentiment and risk factors.

**Role**:
- Analyze news and events that impact the market
- Assess news market impact and sentiment
- Identify potential risk factors and opportunities

**Default Settings**:
| Item | Value |
|------|-------|
| output_format | structured |
| max_tool_calls | 5 |

**output_schema**:
```json
{
  "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"], "description": "Market sentiment"},
  "key_events": {"type": "array", "description": "List of key events"},
  "risk_factors": {"type": "array", "description": "List of risk factors"},
  "reasoning": {"type": "string", "description": "Basis for analysis"}
}
```

**Recommended Tool Nodes**: `HTTPRequestNode`, `OverseasStockMarketDataNode`

### 4. strategist (Chief Strategist)

A chief strategist who synthesizes various analysis results to make final trading decisions.

**Role**:
- Synthesize technical analysis, news analysis, and risk assessment results
- Decide on position entry/exit/hold
- Specify concrete trade quantities and prices

**Default Settings**:
| Item | Value |
|------|-------|
| output_format | structured |
| max_tool_calls | 10 |

**output_schema**:
```json
{
  "action": {"type": "string", "enum": ["buy", "sell", "hold", "reduce"], "description": "Trading decision"},
  "symbol": {"type": "string", "description": "Target symbol"},
  "quantity": {"type": "number", "description": "Trade quantity"},
  "price": {"type": "number", "description": "Limit price (0 for market order)"},
  "confidence": {"type": "number", "description": "Confidence level (0.0 ~ 1.0)"},
  "reasoning": {"type": "string", "description": "Basis for overall judgment"}
}
```

**Recommended Tool Nodes**: `OverseasStockAccountNode`, `OverseasStockMarketDataNode`, `OverseasStockNewOrderNode`, `ConditionNode`

### Multi-Agent Pattern (Chief Strategist + Specialists)

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "AAPL", "exchange": "NASDAQ"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "symbol": "AAPL", "exchange": "NASDAQ",
     "start_date": "{{ date.ago(60, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},

    {"id": "risk_agent", "type": "AIAgentNode",
     "preset": "risk_manager",
     "user_prompt": "Evaluate the risk of current positions."},

    {"id": "tech_agent", "type": "AIAgentNode",
     "preset": "technical_analyst",
     "user_prompt": "Perform a technical analysis of AAPL."},

    {"id": "strategist_agent", "type": "AIAgentNode",
     "preset": "strategist",
     "user_prompt": "Risk management result: {{ nodes.risk_agent.response }}\nTechnical analysis result: {{ nodes.tech_agent.response }}\n\nSynthesize the above analyses and make a final trading decision."}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "history"},
    {"from": "llm", "to": "risk_agent", "type": "ai_model"},
    {"from": "llm", "to": "tech_agent", "type": "ai_model"},
    {"from": "llm", "to": "strategist_agent", "type": "ai_model"},
    {"from": "account", "to": "risk_agent", "type": "tool"},
    {"from": "market", "to": "risk_agent", "type": "tool"},
    {"from": "history", "to": "tech_agent", "type": "tool"},
    {"from": "risk_agent", "to": "strategist_agent"},
    {"from": "tech_agent", "to": "strategist_agent"}
  ]
}
```

**Flow**: Risk Manager + Technical Analyst analyze in parallel → Chief Strategist synthesizes results for final decision

## Output Format Details

### text Mode

```json
{
  "output_format": "text",
  "user_prompt": "Provide a brief analysis of AAPL."
}
```

**Response**: `"AAPL currently has an RSI of 35, in the oversold zone..."`

### json Mode

```json
{
  "output_format": "json",
  "user_prompt": "Respond with your AAPL trading judgment in JSON format: {signal, confidence, reasoning}"
}
```

**Response**: `{"signal": "buy", "confidence": 0.85, "reasoning": "RSI oversold..."}`

JSON parsing behavior:
- Pure JSON string → Direct parsing
- ```json ... ``` block → Extract and parse JSON within block
- ``` ... ``` block (without json keyword) → Extract and parse JSON within block
- Parsing failure → Return raw text string as-is (not an error)

### structured Mode

```json
{
  "output_format": "structured",
  "output_schema": {
    "signal": {"type": "string", "enum": ["buy", "hold", "sell"]},
    "confidence": {"type": "number"},
    "reasoning": {"type": "string"}
  }
}
```

**Response**: `{"signal": "buy", "confidence": 0.85, "reasoning": "..."}`

Pydantic validation behavior:
- If schema has `enum`, validates as Literal type
- Extra fields not in schema are ignored
- Missing required fields or enum violations → Return original dict (not an error, fallback)

## output_schema Field Types

| type | Python Type | Description |
|------|-------------|-------------|
| `"string"` | str | String |
| `"number"` | float | Float |
| `"integer"` | int | Integer |
| `"boolean"` | bool | Boolean |
| `"array"` | list | Array |
| `"object"` | dict | Object |

Additional attributes:
- `enum`: List of allowed values (e.g., `["buy", "sell", "hold"]`)
- `description`: Field description (provides hints to the LLM)

## Preset API (PresetLoader)

```python
from programgarden_core.presets import PresetLoader

# List presets
presets = PresetLoader.list_presets()
# → [{"id": "risk_manager", "name": "Risk Manager", "icon": "🛡️", ...}, ...]

# Get preset IDs
ids = PresetLoader.get_preset_ids()
# → ["risk_manager", "news_analyst", "technical_analyst", "strategist"]

# Load a preset
preset = PresetLoader.load_preset("risk_manager")
# → {"id": "risk_manager", "system_prompt": "...", "output_schema": {...}, ...}

# Apply preset (merge into config)
config = {"user_prompt": "Analyze positions", "output_format": "text"}
result = PresetLoader.apply_preset("risk_manager", config)
# → system_prompt is populated, output_format keeps user setting "text"
```

## Preset Selection Guide

| Purpose | Preset | Key Output |
|---------|--------|------------|
| Position risk assessment | `risk_manager` | risk_level, positions, reasoning |
| Chart/indicator analysis | `technical_analyst` | signal, confidence, support/resistance |
| News impact analysis | `news_analyst` | sentiment, key_events, risk_factors |
| Final trading decision | `strategist` | action, symbol, quantity, price |
| Free-form | `custom` (default) | User-defined |
