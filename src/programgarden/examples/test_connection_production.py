"""
브로커 connection 바인딩 - 프로덕션 방식 테스트

프로덕션 환경에서는 환경변수가 아닌, 워크플로우 JSON의 credentials.data에 
서버가 복호화한 값을 직접 주입합니다.

이 테스트는 프로덕션과 동일한 방식으로 credentials를 전달합니다:
- credentials.data에 appkey, appsecret 값 포함
- secrets 파라미터 사용 안 함

테스트 대상 노드:
1. AccountNode - 계좌 잔고 조회
2. MarketDataNode - 시세 조회 (REST)
3. WatchlistNode - 관심종목 심볼 정규화
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 로컬 테스트용 환경변수 로드 (프로덕션에서는 서버가 처리)
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from programgarden import ProgramGarden


def get_stock_credentials():
    """해외주식 credentials (프로덕션에서는 서버가 DB에서 복호화)"""
    return {
        "appkey": os.getenv("APPKEY"),
        "appsecret": os.getenv("APPSECRET"),
    }


def get_futures_credentials():
    """해외선물 모의투자 credentials"""
    return {
        "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
        "appsecret": os.getenv("APPSECRET_FUTURE_FAKE"),
    }


# ==========================================
# 테스트 1: 해외주식 AccountNode - 프로덕션 방식
# ==========================================
def test_account_production():
    """해외주식 계좌 잔고 조회 - credentials.data에 값 직접 포함"""
    creds = get_stock_credentials()
    
    # 프로덕션 방식: credentials.data에 실제 값 포함
    workflow = {
        "id": "test-account-production",
        "version": "1.0.0",
        "name": "해외주식 계좌 잔고 조회",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "stock-cred",
            },
            {
                "id": "account",
                "type": "AccountNode",
                "connection": "{{ nodes.broker.connection }}",
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
        ],
        "credentials": {
            "stock-cred": {
                "type": "broker_ls",
                "name": "해외주식",
                # 프로덕션: 서버가 복호화하여 여기에 값 주입
                "data": creds,
            }
        },
    }

    pg = ProgramGarden()
    
    print("=" * 70)
    print("테스트 1: AccountNode - 해외주식 계좌 (프로덕션 방식)")
    print("=" * 70)
    print(f"  credentials.data 포함 여부: appkey={'있음' if creds.get('appkey') else '없음'}")
    
    result = pg.validate(workflow)
    if not result.is_valid:
        print(f"❌ 검증 실패: {result.errors}")
        return False
    
    # async로 실행하여 context에서 outputs 직접 접근
    async def run():
        job = await pg.run_async(workflow)
        
        import asyncio
        start = asyncio.get_event_loop().time()
        while job.status in ("pending", "running"):
            await asyncio.sleep(0.1)
            if asyncio.get_event_loop().time() - start > 30:
                break
        
        return job
    
    job = asyncio.run(run())
    
    # context에서 outputs 직접 가져오기
    account = job.context.get_all_outputs("account") or {}
    
    print(f"\n📊 계좌 정보:")
    print(f"  - held_symbols (보유종목): {account.get('held_symbols', [])}")
    
    balance = account.get('balance', {})
    print(f"  - balance (예수금):")
    print(f"      cash_krw: {balance.get('cash_krw', 'N/A')}")
    print(f"      total_eval_krw: {balance.get('total_eval_krw', 'N/A')}")
    
    positions = account.get('positions', {})
    print(f"  - positions: {len(positions)}개")
    
    if positions:
        print("\n  📈 보유 포지션:")
        for symbol, pos in list(positions.items())[:3]:
            print(f"    - {symbol}: {pos.get('qty')}주 @ ${pos.get('avg_price')} (현재 ${pos.get('current_price')})")
    
    status = job.status
    print(f"\n  실행 상태: {status}")
    
    # 성공 여부: completed 상태이고 데이터가 있어야 함
    has_data = len(account.get("held_symbols", [])) > 0 or len(positions) > 0
    return status == "completed" and has_data


# ==========================================
# 테스트 2: 해외선물 모의투자 AccountNode
# ==========================================
def test_futures_account_production():
    """해외선물 모의투자 계좌 - credentials.data에 값 직접 포함"""
    creds = get_futures_credentials()
    
    workflow = {
        "id": "test-futures-production",
        "version": "1.0.0",
        "name": "해외선물 모의투자 계좌",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "paper_trading": True,
                "credential_id": "futures-cred",
            },
            {
                "id": "account",
                "type": "AccountNode",
                "connection": "{{ nodes.broker.connection }}",
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
        ],
        "credentials": {
            "futures-cred": {
                "type": "broker_ls",
                "name": "해외선물 모의투자",
                "data": creds,
            }
        },
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 70)
    print("테스트 2: AccountNode - 해외선물 모의투자 (프로덕션 방식)")
    print("=" * 70)
    print(f"  credentials.data 포함 여부: appkey={'있음' if creds.get('appkey') else '없음'}")
    
    result = pg.validate(workflow)
    if not result.is_valid:
        print(f"❌ 검증 실패: {result.errors}")
        return False
    
    async def run():
        job = await pg.run_async(workflow)
        
        import asyncio
        start = asyncio.get_event_loop().time()
        while job.status in ("pending", "running"):
            await asyncio.sleep(0.1)
            if asyncio.get_event_loop().time() - start > 30:
                break
        
        return job
    
    job = asyncio.run(run())
    
    account = job.context.get_all_outputs("account") or {}
    
    print(f"\n📊 해외선물 모의투자 계좌:")
    print(f"  - held_symbols: {account.get('held_symbols', [])}")
    
    balance = account.get('balance', {})
    print(f"  - balance: {balance}")
    
    positions = account.get('positions', {})
    print(f"  - positions: {len(positions)}개")
    
    status = job.status
    print(f"\n  실행 상태: {status}")
    
    return status == "completed"


# ==========================================
# 테스트 3: MarketDataNode - 시세 조회
# ==========================================
def test_market_data_production():
    """해외주식 시세 조회 - credentials.data에 값 직접 포함"""
    creds = get_stock_credentials()
    
    workflow = {
        "id": "test-market-production",
        "version": "1.0.0",
        "name": "해외주식 시세 조회",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "stock-cred",
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                ],
            },
            {
                "id": "market",
                "type": "MarketDataNode",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "fields": ["price", "change", "volume"],
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "market"},
        ],
        "credentials": {
            "stock-cred": {
                "type": "broker_ls",
                "name": "해외주식",
                "data": creds,
            }
        },
    }

    pg = ProgramGarden()
    
    print("\n" + "=" * 70)
    print("테스트 3: MarketDataNode - 시세 조회 (프로덕션 방식)")
    print("=" * 70)
    print(f"  credentials.data 포함 여부: appkey={'있음' if creds.get('appkey') else '없음'}")
    
    result = pg.validate(workflow)
    if not result.is_valid:
        print(f"❌ 검증 실패: {result.errors}")
        return False
    
    async def run():
        job = await pg.run_async(workflow)
        
        import asyncio
        start = asyncio.get_event_loop().time()
        while job.status in ("pending", "running"):
            await asyncio.sleep(0.1)
            if asyncio.get_event_loop().time() - start > 30:
                break
        
        return job
    
    job = asyncio.run(run())
    
    market = job.context.get_all_outputs("market") or {}
    watchlist = job.context.get_all_outputs("watchlist") or {}
    
    print(f"\n📊 WatchlistNode 출력:")
    symbols = watchlist.get('symbols', [])
    print(f"  - symbols: {symbols}")
    
    print(f"\n📊 MarketDataNode 출력:")
    prices = market.get("prices", {})
    for symbol, data in prices.items():
        print(f"  - {symbol}: ${data.get('price', 'N/A')} ({data.get('change', 'N/A')}%)")
    
    status = job.status
    print(f"\n  실행 상태: {status}")
    
    # 성공 여부: completed 상태이고 가격 데이터가 있어야 함
    has_data = len(prices) > 0
    return status == "completed" and has_data


# ==========================================
# 메인 실행
# ==========================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 프로덕션 방식 Connection 바인딩 테스트")
    print("   (credentials.data에 값 직접 포함, secrets 파라미터 사용 안 함)")
    print("=" * 70)
    
    results = []
    
    # 테스트 1: 해외주식 AccountNode
    try:
        results.append(("해외주식 AccountNode", test_account_production()))
    except Exception as e:
        print(f"❌ 테스트 1 에러: {e}")
        import traceback
        traceback.print_exc()
        results.append(("해외주식 AccountNode", False))
    
    # 테스트 2: 해외선물 AccountNode
    try:
        results.append(("해외선물 AccountNode", test_futures_account_production()))
    except Exception as e:
        print(f"❌ 테스트 2 에러: {e}")
        import traceback
        traceback.print_exc()
        results.append(("해외선물 AccountNode", False))
    
    # 테스트 3: MarketDataNode
    try:
        results.append(("MarketDataNode", test_market_data_production()))
    except Exception as e:
        print(f"❌ 테스트 3 에러: {e}")
        import traceback
        traceback.print_exc()
        results.append(("MarketDataNode", False))
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("📋 테스트 결과 요약 (프로덕션 방식)")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")
    print("=" * 70)
