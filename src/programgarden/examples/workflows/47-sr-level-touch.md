# S/R Level Detection + Touch Check (Overseas Futures Paper Trading)

Detect support/resistance levels from historical data with SupportResistanceLevels, then determine level touch/breakout with LevelTouch. Single underlying (Mini H-Shares).

> 월물(만기) 종목코드를 워크플로우에 적어두지 않습니다. `contract` 노드가 **실행 시점에** 기초자산(미니 H주)의 현재 상장된 **근월물로 자동 해소**하므로, 만기가 지나도 예제가 조용히 멈추지 않습니다.

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Futures)"])
    contract(["FuturesContract
(front month)"])
    hist["Historical
(Overseas Futures)"]
    detect_levels{"Condition
(SupportResistanceLevels)"}
    touch_check{"Condition
(LevelTouch)"}
    if_buy(["If"])
    sr_table[/"TableDisplay"/]
    touch_table[/"TableDisplay"/]
    start --> broker
    broker --> contract
    contract --> hist
    broker --> hist
    hist --> detect_levels
    hist --> touch_check
    detect_levels --> touch_check
    touch_check --> if_buy
    detect_levels --> sr_table
    touch_check --> touch_table
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasFuturesBrokerNode | Overseas futures broker connection (paper trading, HKEX) |
| contract | FuturesContractNode | Resolves the underlying (HMCE) to the currently listed front-month contract at run time |
| hist | OverseasFuturesHistoricalDataNode | Overseas futures historical data query (auto-iterates over `contract.symbols`) |
| detect_levels | ConditionNode | Condition check (plugin-based) |
| touch_check | ConditionNode | Condition check (plugin-based) |
| if_buy | IfNode | Conditional branch (if/else) |
| sr_table | TableDisplayNode | Table display output |
| touch_table | TableDisplayNode | Table display output |

## Key Settings

- **broker**: Paper trading mode
- **contract**: base_products=["HMCE"] (Mini H-Shares), contract_selection=front, futures_exchange=HKEX
- **hist**: symbol=`{{ item }}` — one run per symbol emitted by `contract`
- **detect_levels**: Plugin `SupportResistanceLevels`
- **detect_levels**: lookback=60, swing_strength=3, cluster_tolerance=0.015, min_cluster_size=2
- **touch_check**: Plugin `LevelTouch`
- **touch_check**: levels={{ nodes.detect_levels.symbol_results }}, touch_tolerance=0.01, breakout_threshold=0.015, confirm_bars=2
- **if_buy**: `{{ nodes.touch_check.result }}` == `True`

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_futures | LS Securities Overseas Futures API (paper trading, HKEX only) |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasFuturesBrokerNode)
1. **broker** (OverseasFuturesBrokerNode) --> **contract** (FuturesContractNode)
1. **contract** (FuturesContractNode) --> **hist** (OverseasFuturesHistoricalDataNode)
1. **broker** (OverseasFuturesBrokerNode) --> **hist** (OverseasFuturesHistoricalDataNode)
1. **hist** (OverseasFuturesHistoricalDataNode) --> **detect_levels** (ConditionNode)
1. **hist** (OverseasFuturesHistoricalDataNode) --> **touch_check** (ConditionNode)
1. **detect_levels** (ConditionNode) --> **touch_check** (ConditionNode)
1. **touch_check** (ConditionNode) --> **if_buy** (IfNode)
1. **detect_levels** (ConditionNode) --> **sr_table** (TableDisplayNode)
1. **touch_check** (ConditionNode) --> **touch_table** (TableDisplayNode)
