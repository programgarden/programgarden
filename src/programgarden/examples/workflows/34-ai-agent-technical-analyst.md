# AI Technical Analyst (Chart Analysis)

Query historical data as tool with technical_analyst preset and perform technical analysis

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Stock)"])
    llm["LLMModel"]
    historical["Historical
(Overseas Stock)"]
    market["MarketData
(Overseas Stock)"]
    agent["AIAgent"]
    summary[/"SummaryDisplay"/]
    start --> broker
    start --> llm
    broker --> historical
    broker --> market
    llm --> agent
    historical --> agent
    market --> agent
    agent --> summary
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasStockBrokerNode | Overseas stock broker connection |
| llm | LLMModelNode | LLM model connection |
| historical | OverseasStockHistoricalDataNode | Overseas stock historical data query |
| market | OverseasStockMarketDataNode | Overseas stock market data query |
| agent | AIAgentNode | AI agent (tool-based analysis) |
| summary | SummaryDisplayNode | Summary dashboard |

## Key Settings

- **market**: NVDA
- **agent**: preset=`technical_analyst`

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_stock | LS Securities Overseas Stock API |
| llm_cred | llm_anthropic | Anthropic Claude API |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasStockBrokerNode)
1. **start** (StartNode) --> **llm** (LLMModelNode)
1. **broker** (OverseasStockBrokerNode) --> **historical** (OverseasStockHistoricalDataNode)
1. **broker** (OverseasStockBrokerNode) --> **market** (OverseasStockMarketDataNode)
1. **llm** (LLMModelNode) --> **agent** (AIAgentNode)
1. **historical** (OverseasStockHistoricalDataNode) --> **agent** (AIAgentNode)
1. **market** (OverseasStockMarketDataNode) --> **agent** (AIAgentNode)
1. **agent** (AIAgentNode) --> **summary** (SummaryDisplayNode)

## How to Run

```python
from programgarden import ProgramGarden

pg = ProgramGarden()
job = await pg.run_async(workflow)
```
