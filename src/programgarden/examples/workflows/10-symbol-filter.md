# Symbol Filtering (Watchlist - Positions)

관심종목에서 보유종목을 제외(difference)하여 미보유 종목만 추출한 뒤, 해당 종목들의 현재 시세를 조회하는 워크플로우입니다.

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Stock)"])
    watchlist["Watchlist"]
    account["Account
(Overseas Stock)"]
    filter["SymbolFilter"]
    market["MarketData
(Overseas Stock)"]
    start --> broker
    broker --> watchlist
    broker --> account
    watchlist --> filter
    account --> filter
    filter --> market
```

## Node Configuration

| ID | Type | Key Config |
|----|------|------------|
| start | StartNode | — |
| broker | OverseasStockBrokerNode | credential_id: `broker_cred` |
| watchlist | WatchlistNode | symbols: AAPL, TSLA, NVDA, MSFT(NASDAQ), JPM(NYSE) |
| account | OverseasStockAccountNode | — (broker connection 자동 주입) |
| filter | SymbolFilterNode | operation: `difference` |
| market | OverseasStockMarketDataNode | symbol: `{{ item }}` (auto-iterate) |

## Expression Bindings

| Node | Field | Expression | Description |
|------|-------|------------|-------------|
| filter | input_a | `{{ nodes.watchlist.symbols }}` | 관심종목 배열 (A집합) |
| filter | input_b | `{{ nodes.account.held_symbols }}` | 보유종목 배열 (B집합) |
| market | symbol | `{{ item }}` | filter 출력 배열의 각 종목 (auto-iterate) |

## Required Credentials

| ID | Type | Fields |
|----|------|--------|
| broker_cred | broker_ls_overseas_stock | appkey, appsecret |

## Execution Flow

1. **start** → **broker**: LS증권 해외주식 API 로그인
2. **broker** → **watchlist**, **account** (병렬 분기):
   - **watchlist**: 5개 관심종목 배열 출력 → `symbols` 포트
   - **account**: 계좌 조회 → `held_symbols` 포트 (보유 종목 심볼 배열)
3. **watchlist**, **account** → **filter**:
   - `input_a`(관심종목 5개) - `input_b`(보유종목) = 미보유 종목만 추출
   - 출력: `symbols` 배열, `count` 정수
4. **filter** → **market** (auto-iterate):
   - filter의 `symbols`가 배열이고 market의 symbol이 `{{ item }}` → 종목별 반복 실행
   - 예: 미보유 3종목이면 MarketDataNode가 3번 실행됨

## Expected Output

**account** 노드:
| Port | Type | Description |
|------|------|-------------|
| held_symbols | symbol_list | 보유종목 심볼 배열 `[{symbol, exchange}, ...]` |
| balance | balance_data | 예수금/주문가능금액 등 잔고 정보 |
| positions | position_data | 보유종목 상세 배열 `[{symbol, exchange, quantity, avg_price, pnl, pnl_rate, ...}]` |

**filter** 노드:
| Port | Type | Description |
|------|------|-------------|
| symbols | symbol_list | 필터링된 종목 배열 `[{symbol, exchange}, ...]` |
| count | integer | 결과 종목 수 |

**market** 노드 (종목별 반복):
| Port | Type | Description |
|------|------|-------------|
| value | market_data | 현재가, 전일대비, 거래량 등 시세 데이터 |

## Notes

- **SymbolFilterNode operation 종류**: `difference`(A-B), `intersection`(A∩B), `union`(A∪B)
- **auto-iterate**: filter → market 구간에서 배열 출력 + `{{ item }}` 바인딩 = 종목별 자동 반복 실행
- **broker connection 자동 주입**: AccountNode, MarketDataNode는 BrokerNode와 edge 연결만으로 connection을 받음 (별도 바인딩 불필요)
- **held_symbols vs positions**: SymbolFilterNode에는 심볼만 필요하므로 `held_symbols` 포트 사용 (`positions`는 상세 포지션 데이터)
