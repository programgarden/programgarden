"""
브로커 connection 바인딩 표준화 테스트

Phase 6 검증: 각 노드에서 connection 바인딩이 정상 동작하는지 테스트

테스트 시나리오:
1. 해외주식 실계좌 - AccountNode
2. 해외주식 실계좌 - MarketDataNode
3. 해외선물 모의투자 - AccountNode
4. 해외주식 - RealMarketDataNode (간략 테스트)
"""

import asyncio
import os
from pathlib import Path

# .env 파일 로드
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from programgarden import ProgramGarden


# ==========================================
# 테스트 1: 해외주식 실계좌 - AccountNode (명시적 connection 바인딩)
# ==========================================
def test_overseas_stock_account():
    """해외주식 AccountNode connection 바인딩 테스트"""
    workflow = {
        "id": "test-overseas-stock-account",
        "version": "1.0.0",
        "name": "해외주식 계좌 조회 (connection 바인딩)",
        "description": "AccountNode에서 명시적 connection 바인딩 테스트",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "overseas-stock-cred",
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "account",
                "type": "AccountNode",
                # 명시적 connection 바인딩 (핵심 테스트 포인트!)
                "connection": "{{ nodes.broker.connection }}",
                "position": {"x": 500, "y": 100},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
        ],
        "credentials": {
            "overseas-stock-cred": {
                "type": "broker_ls",
                "name": "LS증권 해외주식 실계좌",
                "data": {"appkey": "", "appsecret": ""},
            }
        },
    }

    # 실행시 secrets로 실제 키 전달
    secrets = {
        "overseas-stock-cred": {
            "appkey": os.getenv("APPKEY"),
            "appsecret": os.getenv("APPSECRET"),
        }
    }

    pg = ProgramGarden()
    
    print("=" * 60)
    print("테스트 1: 해외주식 AccountNode (connection 바인딩)")
    print("=" * 60)
    
    # 검증
    result = pg.validate(workflow)
    print(f"검증 결과: {'✅ 통과' if result.is_valid else '❌ 실패'}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    # 실행
    print("\n실행 중...")
    job = pg.run(workflow, secrets=secrets, timeout=30.0)
    
    print(f"\n실행 결과: {job.get('status', 'unknown')}")
    
    # account 노드 출력 확인
    outputs = job.get("outputs", {})
    account_output = outputs.get("account", {})
    
    print(f"\n📊 AccountNode 출력:")
    print(f"  - balance: {account_output.get('balance', 'N/A')}")
    print(f"  - held_symbols: {account_output.get('held_symbols', [])}")
    
    return job.get("status") == "completed"


# ==========================================
# 테스트 2: 해외주식 - MarketDataNode (connection 바인딩)
# ==========================================
def test_overseas_stock_market_data():
    """해외주식 MarketDataNode connection 바인딩 테스트"""
    workflow = {
        "id": "test-overseas-stock-market",
        "version": "1.0.0",
        "name": "해외주식 시세 조회 (connection 바인딩)",
        "description": "MarketDataNode에서 명시적 connection 바인딩 테스트",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "overseas-stock-cred",
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                # WatchlistNode도 명시적 connection 바인딩!
                "connection": "{{ nodes.broker.connection }}",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                ],
                "position": {"x": 300, "y": 250},
            },
            {
                "id": "market",
                "type": "MarketDataNode",
                # MarketDataNode 명시적 connection 바인딩!
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "fields": ["price", "volume", "change_rate"],
                "position": {"x": 500, "y": 175},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "broker", "to": "market"},
            {"from": "watchlist", "to": "market"},
        ],
        "credentials": {
            "overseas-stock-cred": {
                "type": "broker_ls",
                "name": "LS증권 해외주식 실계좌",
                "data": {"appkey": "", "appsecret": ""},
            }
        },
    }

    secrets = {
        "overseas-stock-cred": {
            "appkey": os.getenv("APPKEY"),
            "appsecret": os.getenv("APPSECRET"),
        }
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 60)
    print("테스트 2: 해외주식 MarketDataNode (connection 바인딩)")
    print("=" * 60)
    
    result = pg.validate(workflow)
    print(f"검증 결과: {'✅ 통과' if result.is_valid else '❌ 실패'}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    print("\n실행 중...")
    job = pg.run(workflow, secrets=secrets, timeout=30.0)
    
    print(f"\n실행 결과: {job.get('status', 'unknown')}")
    
    outputs = job.get("outputs", {})
    market_output = outputs.get("market", {})
    
    print(f"\n📊 MarketDataNode 출력:")
    print(f"  - prices: {market_output.get('prices', {})}")
    
    return job.get("status") == "completed"


# ==========================================
# 테스트 3: 해외선물 모의투자 - AccountNode
# ==========================================
def test_overseas_futures_paper():
    """해외선물 모의투자 AccountNode connection 바인딩 테스트"""
    workflow = {
        "id": "test-futures-paper-account",
        "version": "1.0.0",
        "name": "해외선물 모의투자 계좌 조회",
        "description": "해외선물 모의투자 AccountNode connection 바인딩 테스트",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "broker_futures",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "paper_trading": True,  # 모의투자 모드
                "credential_id": "futures-paper-cred",
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "account",
                "type": "AccountNode",
                # 명시적 connection 바인딩 - broker_futures 참조
                "connection": "{{ nodes.broker_futures.connection }}",
                "position": {"x": 500, "y": 100},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker_futures"},
            {"from": "broker_futures", "to": "account"},
        ],
        "credentials": {
            "futures-paper-cred": {
                "type": "broker_ls",
                "name": "LS증권 해외선물 모의투자",
                "data": {"appkey": "", "appsecret": ""},
            }
        },
    }

    secrets = {
        "futures-paper-cred": {
            "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
            "appsecret": os.getenv("APPSECRET_FUTURE_FAKE"),
        }
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 60)
    print("테스트 3: 해외선물 모의투자 AccountNode (connection 바인딩)")
    print("=" * 60)
    
    result = pg.validate(workflow)
    print(f"검증 결과: {'✅ 통과' if result.is_valid else '❌ 실패'}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    print("\n실행 중...")
    job = pg.run(workflow, secrets=secrets, timeout=30.0)
    
    print(f"\n실행 결과: {job.get('status', 'unknown')}")
    
    outputs = job.get("outputs", {})
    account_output = outputs.get("account", {})
    
    print(f"\n📊 AccountNode 출력 (해외선물 모의투자):")
    print(f"  - balance: {account_output.get('balance', 'N/A')}")
    print(f"  - held_symbols: {account_output.get('held_symbols', [])}")
    
    return job.get("status") == "completed"


# ==========================================
# 테스트 4: 다중 브로커 시나리오 (connection 바인딩 구분)
# ==========================================
def test_multiple_brokers():
    """다중 브로커 환경에서 connection 바인딩 정확성 테스트"""
    workflow = {
        "id": "test-multiple-brokers",
        "version": "1.0.0",
        "name": "다중 브로커 connection 바인딩",
        "description": "2개의 BrokerNode에서 각각 다른 AccountNode 연결",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "position": {"x": 100, "y": 200},
            },
            # 브로커 1: 해외주식 실계좌
            {
                "id": "broker_stock",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "stock-cred",
                "position": {"x": 300, "y": 100},
            },
            # 브로커 2: 해외선물 모의투자
            {
                "id": "broker_futures",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "paper_trading": True,
                "credential_id": "futures-cred",
                "position": {"x": 300, "y": 300},
            },
            # AccountNode 1: 해외주식 브로커 연결
            {
                "id": "account_stock",
                "type": "AccountNode",
                "connection": "{{ nodes.broker_stock.connection }}",  # 명시적!
                "position": {"x": 500, "y": 100},
            },
            # AccountNode 2: 해외선물 브로커 연결
            {
                "id": "account_futures",
                "type": "AccountNode",
                "connection": "{{ nodes.broker_futures.connection }}",  # 명시적!
                "position": {"x": 500, "y": 300},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker_stock"},
            {"from": "start", "to": "broker_futures"},
            {"from": "broker_stock", "to": "account_stock"},
            {"from": "broker_futures", "to": "account_futures"},
        ],
        "credentials": {
            "stock-cred": {
                "type": "broker_ls",
                "name": "해외주식 실계좌",
                "data": {"appkey": "", "appsecret": ""},
            },
            "futures-cred": {
                "type": "broker_ls",
                "name": "해외선물 모의투자",
                "data": {"appkey": "", "appsecret": ""},
            },
        },
    }

    secrets = {
        "stock-cred": {
            "appkey": os.getenv("APPKEY"),
            "appsecret": os.getenv("APPSECRET"),
        },
        "futures-cred": {
            "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
            "appsecret": os.getenv("APPSECRET_FUTURE_FAKE"),
        },
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 60)
    print("테스트 4: 다중 브로커 connection 바인딩")
    print("=" * 60)
    print("  - broker_stock (overseas_stock) → account_stock")
    print("  - broker_futures (overseas_futures/paper) → account_futures")
    
    result = pg.validate(workflow)
    print(f"\n검증 결과: {'✅ 통과' if result.is_valid else '❌ 실패'}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    print("\n실행 중...")
    job = pg.run(workflow, secrets=secrets, timeout=60.0)
    
    print(f"\n실행 결과: {job.get('status', 'unknown')}")
    
    outputs = job.get("outputs", {})
    
    print(f"\n📊 account_stock 출력:")
    stock_out = outputs.get("account_stock", {})
    print(f"  - balance: {stock_out.get('balance', 'N/A')}")
    
    print(f"\n📊 account_futures 출력:")
    futures_out = outputs.get("account_futures", {})
    print(f"  - balance: {futures_out.get('balance', 'N/A')}")
    
    return job.get("status") == "completed"


# ==========================================
# 테스트 5: RealMarketDataNode (connection 바인딩)
# ==========================================
def test_real_market_data():
    """RealMarketDataNode connection 바인딩 테스트 (검증만)"""
    workflow = {
        "id": "test-realmarket-connection",
        "version": "1.0.0",
        "name": "실시간 시세 connection 바인딩",
        "description": "RealMarketDataNode에서 명시적 connection 바인딩 테스트",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "position": {"x": 100, "y": 100},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "stock-cred",
                "position": {"x": 300, "y": 100},
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
                "position": {"x": 300, "y": 250},
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                # 명시적 connection 바인딩!
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "fields": ["price", "volume"],
                "stay_connected": False,  # 1회만 실행
                "position": {"x": 500, "y": 175},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "broker", "to": "realMarket"},
            {"from": "watchlist", "to": "realMarket"},
        ],
        "credentials": {
            "stock-cred": {
                "type": "broker_ls",
                "name": "LS증권 해외주식",
                "data": {"appkey": "", "appsecret": ""},
            }
        },
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 60)
    print("테스트 5: RealMarketDataNode (connection 바인딩 검증)")
    print("=" * 60)
    
    # 검증만 수행 (WebSocket 연결 테스트는 시간이 오래 걸림)
    result = pg.validate(workflow)
    print(f"검증 결과: {'✅ 통과' if result.is_valid else '❌ 실패'}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    print("  ✅ RealMarketDataNode에 connection 바인딩 정상 인식")
    return True


# ==========================================
# 메인 실행
# ==========================================
if __name__ == "__main__":
    print("\n🧪 브로커 connection 바인딩 표준화 테스트")
    print("=" * 60)
    
    results = []
    
    # 테스트 1: 해외주식 AccountNode
    try:
        results.append(("해외주식 AccountNode", test_overseas_stock_account()))
    except Exception as e:
        print(f"❌ 테스트 1 실패: {e}")
        results.append(("해외주식 AccountNode", False))
    
    # 테스트 2: 해외주식 MarketDataNode
    try:
        results.append(("해외주식 MarketDataNode", test_overseas_stock_market_data()))
    except Exception as e:
        print(f"❌ 테스트 2 실패: {e}")
        results.append(("해외주식 MarketDataNode", False))
    
    # 테스트 3: 해외선물 모의투자
    try:
        results.append(("해외선물 모의투자", test_overseas_futures_paper()))
    except Exception as e:
        print(f"❌ 테스트 3 실패: {e}")
        results.append(("해외선물 모의투자", False))
    
    # 테스트 4: 다중 브로커
    try:
        results.append(("다중 브로커", test_multiple_brokers()))
    except Exception as e:
        print(f"❌ 테스트 4 실패: {e}")
        results.append(("다중 브로커", False))
    
    # 테스트 5: RealMarketDataNode (검증만)
    try:
        results.append(("RealMarketDataNode", test_real_market_data()))
    except Exception as e:
        print(f"❌ 테스트 5 실패: {e}")
        results.append(("RealMarketDataNode", False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")
    print("=" * 60)
