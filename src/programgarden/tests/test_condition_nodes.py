"""
Phase 3: Condition Category 노드 실제 API 테스트

테스트 대상:
1. ConditionNode (RSI 플러그인) - 해외주식/해외선물
2. LogicNode (all 연산자) - 해외주식/해외선물

실행 방법:
    cd src/programgarden && poetry run python examples/test_condition_nodes.py
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# .env 로드 (programgarden 폴더 기준)
env_path = Path(__file__).parent.parent.parent.parent / ".env"
print(f"🔍 Looking for .env at: {env_path}")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    print(f"✅ Loaded .env")
else:
    print(f"⚠️ .env not found at {env_path}")

# 암호화 유틸리티
workflow_editor_path = Path(__file__).parent.parent / "examples" / "workflow_editor"
sys.path.insert(0, str(workflow_editor_path))
from encryption import decrypt_data

# ProgramGarden
from programgarden import WorkflowExecutor


def load_credentials():
    """credentials.json 로드 및 복호화"""
    cred_path = workflow_editor_path / "credentials.json"
    
    with open(cred_path) as f:
        data = json.load(f)
    
    credentials = {}
    for cred in data.get("credentials", []):
        cred_id = cred["id"]
        encrypted_data = cred.get("data", "{}")
        decrypted = decrypt_data(encrypted_data)
        credentials[cred["name"]] = {
            "id": cred_id,
            "type": cred["credential_type"],
            **decrypted
        }
        print(f"✅ Loaded credential: {cred['name']} (appkey: {decrypted.get('appkey', 'N/A')[:8]}...)")
    
    return credentials


async def test_condition_node_stock(credentials):
    """ConditionNode RSI 테스트 - 해외주식"""
    print("\n" + "="*60)
    print("🧪 TEST 1: ConditionNode (RSI) - 해외주식")
    print("="*60)
    
    cred = credentials.get("LS 해외주식", {})
    if not cred or not cred.get("appkey"):
        print("❌ LS 해외주식 credential not found or empty")
        return False
    
    workflow = {
        "id": "test-condition-stock",
        "name": "Test ConditionNode RSI - Stock",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "broker-cred"
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"}
                ]
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "stay_connected": False
            },
            {
                "id": "rsiCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                "price_data": "{{ nodes.realMarket.price }}",
                "symbols": "{{ nodes.watchlist.symbols }}"
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsiCondition"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_stock",
                "name": "LS증권 API",
                "data": {
                    "appkey": cred.get("appkey", ""),
                    "appsecret": cred.get("appsecret", ""),
                    "paper_trading": cred.get("paper_trading", False)
                }
            }
        ]
    }
    
    try:
        executor = WorkflowExecutor()
        job = await executor.execute(workflow)
        
        # Job이 완료될 때까지 대기
        await asyncio.sleep(5)  # 실시간 데이터 수신 대기
        await job.stop()
        
        # rsiCondition 결과 확인
        rsi_result = job.context.get_all_outputs("rsiCondition")
        print(f"✅ RSI Condition Result:")
        print(f"   - passed: {rsi_result.get('result', {}).get('passed', 'N/A') if isinstance(rsi_result.get('result'), dict) else rsi_result.get('passed', 'N/A')}")
        print(f"   - passed_symbols: {rsi_result.get('passed_symbols', [])}")
        print(f"   - values: {rsi_result.get('values', {})}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_condition_node_futures(credentials):
    """ConditionNode RSI 테스트 - 해외선물"""
    print("\n" + "="*60)
    print("🧪 TEST 2: ConditionNode (RSI) - 해외선물 모의투자")
    print("="*60)
    
    cred = credentials.get("LS 해외선물 모의투자", {})
    if not cred or not cred.get("appkey"):
        print("❌ LS 해외선물 모의투자 credential not found or empty")
        return False
    
    workflow = {
        "id": "test-condition-futures",
        "name": "Test ConditionNode RSI - Futures",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "credential_id": "broker-cred"
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [
                    {"exchange": "CME", "symbol": "NQH25"}
                ]
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "stay_connected": False
            },
            {
                "id": "rsiCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 30, "direction": "below"},
                "price_data": "{{ nodes.realMarket.price }}",
                "symbols": "{{ nodes.watchlist.symbols }}"
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsiCondition"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_futures",
                "name": "LS증권 선물 API",
                "data": {
                    "appkey": cred.get("appkey", ""),
                    "appsecret": cred.get("appsecret", ""),
                    "paper_trading": cred.get("paper_trading", True)
                }
            }
        ]
    }
    
    try:
        executor = WorkflowExecutor()
        job = await executor.execute(workflow)
        
        # Job이 완료될 때까지 대기
        await asyncio.sleep(5)
        await job.stop()
        
        rsi_result = job.context.get_all_outputs("rsiCondition")
        print(f"✅ RSI Condition Result:")
        print(f"   - passed: {rsi_result.get('passed', 'N/A')}")
        print(f"   - passed_symbols: {rsi_result.get('passed_symbols', [])}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_logic_node_stock(credentials):
    """LogicNode all 연산자 테스트 - 해외주식"""
    print("\n" + "="*60)
    print("🧪 TEST 3: LogicNode (all) - 해외주식")
    print("="*60)
    
    cred = credentials.get("LS 해외주식", {})
    if not cred or not cred.get("appkey"):
        print("❌ LS 해외주식 credential not found or empty")
        return False
    
    workflow = {
        "id": "test-logic-stock",
        "name": "Test LogicNode ALL - Stock",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode", "category": "infra"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "broker-cred"
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"}
                ]
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "stay_connected": False
            },
            {
                "id": "rsiCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {"period": 14, "threshold": 70, "direction": "below"},
                "price_data": "{{ nodes.realMarket.price }}",
                "symbols": "{{ nodes.watchlist.symbols }}"
            },
            {
                "id": "macdCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MACD",
                "fields": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal": "bullish_cross"},
                "price_data": "{{ nodes.realMarket.price }}",
                "symbols": "{{ nodes.watchlist.symbols }}"
            },
            {
                "id": "logic",
                "type": "LogicNode",
                "category": "condition",
                "operator": "all",
                "conditions": ["rsiCondition", "macdCondition"]
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "rsiCondition"},
            {"from": "realMarket", "to": "macdCondition"},
            {"from": "rsiCondition", "to": "logic"},
            {"from": "macdCondition", "to": "logic"}
        ],
        "credentials": [
            {
                "id": "broker-cred",
                "type": "broker_ls_stock",
                "name": "LS증권 API",
                "data": {
                    "appkey": cred.get("appkey", ""),
                    "appsecret": cred.get("appsecret", ""),
                    "paper_trading": cred.get("paper_trading", False)
                }
            }
        ]
    }
    
    try:
        executor = WorkflowExecutor()
        job = await executor.execute(workflow)
        
        # Job이 완료될 때까지 대기
        await asyncio.sleep(5)
        await job.stop()
        
        logic_result = job.context.get_all_outputs("logic")
        print(f"✅ Logic Node Result:")
        print(f"   - result: {logic_result.get('result', 'N/A')}")
        print(f"   - passed_symbols: {logic_result.get('passed_symbols', [])}")
        print(f"   - details: {logic_result.get('details', {})}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("🚀 Phase 3: Condition Category 노드 API 테스트")
    print("=" * 60)
    
    # Credentials 로드
    credentials = load_credentials()
    print(f"\n📋 Loaded {len(credentials)} credentials")
    
    results = {}
    
    # 테스트 실행
    results["ConditionNode-Stock"] = await test_condition_node_stock(credentials)
    results["ConditionNode-Futures"] = await test_condition_node_futures(credentials)
    results["LogicNode-Stock"] = await test_logic_node_stock(credentials)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    print(f"\n총 {passed_count}/{len(results)} 테스트 통과")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
