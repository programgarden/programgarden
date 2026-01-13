"""02_condition/06_manual_binding - 수동 바인딩 예제

명시적 {{ nodes.xxx.yyy }} 표현식을 사용하여 모든 데이터 소스를 직접 지정하는 예제.

시나리오:
- 일봉 HistoricalDataNode: RSI 계산용 (price_data)
- 실시간 RealMarketDataNode: 거래량 급증 감지 (volume_data)
- AccountNode: 보유 종목 및 포지션 (held_symbols, position_data)
- 두 개 이상의 데이터 소스가 있을 때 각 조건 노드가 원하는 소스를 명시적으로 참조

포트 바인딩 필드:
- price_data: 가격 데이터 (OHLCV)
- volume_data: 거래량 데이터
- symbols: 종목 리스트
- held_symbols: 보유 종목 리스트
- position_data: 포지션 데이터 (평단가, 수량 등)
"""


def get_workflow():
    return {
        "id": "condition-06-manual-binding",
        "version": "1.0.0",
        "name": "수동 바인딩 예제 (모든 데이터 타입)",
        "description": "price_data, volume_data, held_symbols, position_data 모두 명시적 {{ }} 바인딩",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 250},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "position": {"x": 200, "y": 250},
            },
            # === 종목 소스 ===
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "TSLA"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                    {"exchange": "NASDAQ", "symbol": "MSFT"},
                ],
                "position": {"x": 350, "y": 100},
            },
            # === 실시간 데이터 (현재가 + 거래량) ===
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price", "volume"],
                "position": {"x": 350, "y": 250},
            },
            # === 일봉 히스토리 데이터 (RSI 계산용) ===
            {
                "id": "dailyHistory",
                "type": "HistoricalDataNode",
                "category": "data",
                "period": "D",  # 일봉
                "count": 50,    # 50일치
                "position": {"x": 350, "y": 400},
            },
            # === 계좌 정보 (보유 종목 + 포지션) ===
            {
                "id": "account",
                "type": "AccountNode",
                "category": "account",
                "position": {"x": 550, "y": 400},
            },
            # === 조건 1: RSI - 일봉 데이터 사용 ===
            {
                "id": "rsi",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                # === 수동 바인딩: 일봉 데이터를 명시적으로 지정 ===
                "price_data": "{{ nodes.dailyHistory.ohlcv }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "position": {"x": 600, "y": 100},
            },
            # === 조건 2: VolumeSpike - 실시간 거래량 사용 ===
            {
                "id": "volumeSpike",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "VolumeSpike",
                "fields": {"multiplier": 2.0, "lookback": 20},
                # === 수동 바인딩: 실시간 거래량 명시적 지정 ===
                "price_data": "{{ nodes.realMarket.price }}",
                "volume_data": "{{ nodes.realMarket.volume }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "position": {"x": 600, "y": 250},
            },
            # === 조건 3: ProfitTarget - 포지션 데이터 사용 ===
            {
                "id": "profitTarget",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "ProfitTarget",
                "fields": {"target_percent": 10.0},
                # === 수동 바인딩: 계좌 포지션 명시적 지정 ===
                "price_data": "{{ nodes.realMarket.price }}",
                "position_data": "{{ nodes.account.positions }}",
                "held_symbols": "{{ nodes.account.held_symbols }}",
                "symbols": "{{ nodes.account.held_symbols }}",
                "position": {"x": 600, "y": 400},
            },
            # === 로직 노드: 조건 결합 ===
            {
                "id": "logic",
                "type": "LogicNode",
                "category": "condition",
                "mode": "OR",
                "position": {"x": 800, "y": 250},
            },
            # === 디스플레이 ===
            {
                "id": "display",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "fields": ["symbol", "condition", "value", "passed"],
                "position": {"x": 1000, "y": 250},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "broker", "to": "realMarket"},
            {"from": "broker", "to": "account"},
            {"from": "watchlist", "to": "dailyHistory"},
            {"from": "watchlist", "to": "realMarket"},
            # 모든 데이터 소스가 조건 노드들의 upstream
            {"from": "dailyHistory", "to": "rsi"},
            {"from": "realMarket", "to": "rsi"},
            {"from": "realMarket", "to": "volumeSpike"},
            {"from": "realMarket", "to": "profitTarget"},
            {"from": "account", "to": "profitTarget"},
            # 조건들을 로직 노드로 결합
            {"from": "rsi", "to": "logic"},
            {"from": "volumeSpike", "to": "logic"},
            {"from": "profitTarget", "to": "logic"},
            {"from": "logic", "to": "display"},
        ],
    }

