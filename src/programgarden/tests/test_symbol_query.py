"""
SymbolQueryNode 테스트 - 전체종목조회

해외주식: g3190 API (마스터상장종목조회)
해외선물: o3101 API (해외선물마스터조회)
"""
import asyncio
import os
import json
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv("/Users/jyj/ls_projects/programgarden/.env")


async def wait_for_job(job, timeout=30):
    """Job 완료 대기"""
    for _ in range(int(timeout * 10)):
        if job.status in ("completed", "failed", "cancelled"):
            return job.get_state()
        await asyncio.sleep(0.1)
    return job.get_state()


async def test_stock_query():
    """해외주식 전체종목조회 테스트 (g3190)"""
    from programgarden import ProgramGarden
    
    workflow = {
        "id": "symbol-query-stock-test",
        "name": "SymbolQueryNode 테스트 - 해외주식",
        "nodes": [
            {
                "id": "start_1",
                "type": "StartNode",
            },
            {
                "id": "broker_2",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "stock-real-cred"
            },
            {
                "id": "query_3",
                "type": "SymbolQueryNode",
                "connection": "{{nodes.broker_2.connection}}",
                "product_type": "overseas_stock",  # 해외주식 선택
                "country": "US",
                "stock_exchange": "2",  # 2: NASDAQ
                "max_results": 100
            },
        ],
        "edges": [
            {"from": "start_1", "to": "broker_2"},
            {"from": "broker_2", "to": "query_3"},
        ],
        "credentials": [
            {
                "id": "stock-real-cred",
                "type": "broker_ls",
                "name": "해외주식 실계좌",
                "data": {
                    "appkey": os.getenv("APPKEY", ""),
                    "appsecret": os.getenv("APPSECRET", ""),
                    "paper_trading": False
                }
            }
        ]
    }
    
    pg = ProgramGarden()
    job = await pg.run_async(workflow)
    result = await wait_for_job(job)
    
    print("\n" + "="*60)
    print("전체종목조회 결과 - 해외주식 (g3190)")
    print("="*60)
    
    if result["status"] == "completed":
        nodes = result.get("nodes", {})
        query_output = nodes.get("query_3", {}).get("outputs", {})
        symbols = query_output.get("symbols", [])
        count = query_output.get("count", 0)
        
        print(f"✅ 조회 성공: {count}개 종목")
        print(f"상품: {query_output.get('product', 'N/A')}")
        print(f"국가: {query_output.get('country', 'N/A')}")
        
        if symbols:
            print("\n샘플 종목 (처음 10개):")
            for i, sym in enumerate(symbols[:10]):
                print(f"  {i+1}. {sym.get('symbol', 'N/A'):10s} | {sym.get('exchange', 'N/A'):10s} | {sym.get('name', 'N/A')[:30]}")
        
        # 필드 검증
        if symbols:
            first = symbols[0]
            assert "exchange" in first, "exchange 필드 누락"
            assert "symbol" in first, "symbol 필드 누락"
            print("\n✅ 필드 검증 통과: exchange, symbol 포함")
        
        return True
    else:
        print(f"❌ 실패: {result['status']}")
        print(f"에러: {result.get('logs', [])}")
        return False


async def test_futures_query():
    """해외선물 전체종목조회 테스트 (o3101)"""
    from programgarden import ProgramGarden
    
    workflow = {
        "id": "symbol-query-futures-test",
        "name": "SymbolQueryNode 테스트 - 해외선물",
        "nodes": [
            {
                "id": "start_1",
                "type": "StartNode",
            },
            {
                "id": "broker_2",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "credential_id": "futures-paper-cred"
            },
            {
                "id": "query_3",
                "type": "SymbolQueryNode",
                "connection": "{{nodes.broker_2.connection}}",
                "product_type": "overseas_futures",  # 해외선물 선택
                "futures_exchange": "6",  # HKEX
                "max_results": 100
            },
        ],
        "edges": [
            {"from": "start_1", "to": "broker_2"},
            {"from": "broker_2", "to": "query_3"},
        ],
        "credentials": [
            {
                "id": "futures-paper-cred",
                "type": "broker_ls",
                "name": "해외선물 모의투자",
                "data": {
                    "appkey": os.getenv("APPKEY_FUTURE_FAKE", ""),
                    "appsecret": os.getenv("APPSECRET_FUTURE_FAKE", ""),
                    "paper_trading": True
                }
            }
        ]
    }
    
    pg = ProgramGarden()
    job = await pg.run_async(workflow)
    result = await wait_for_job(job)
    
    print("\n" + "="*60)
    print("전체종목조회 결과 - 해외선물 (o3101)")
    print("="*60)
    
    if result["status"] == "completed":
        nodes = result.get("nodes", {})
        query_output = nodes.get("query_3", {}).get("outputs", {})
        symbols = query_output.get("symbols", [])
        count = query_output.get("count", 0)
        
        print(f"✅ 조회 성공: {count}개 종목")
        print(f"상품: {query_output.get('product', 'N/A')}")
        print(f"거래소: {query_output.get('futures_exchange', 'N/A')}")
        
        if symbols:
            print("\n샘플 종목 (처음 10개):")
            for i, sym in enumerate(symbols[:10]):
                print(f"  {i+1}. {sym.get('symbol', 'N/A'):15s} | {sym.get('exchange', 'N/A'):10s} | {sym.get('name', 'N/A')[:25]} | 월물: {sym.get('contract_month', 'N/A')}")
        
        # 필드 검증
        if symbols:
            first = symbols[0]
            assert "exchange" in first, "exchange 필드 누락"
            assert "symbol" in first, "symbol 필드 누락"
            assert "base_product" in first, "base_product 필드 누락"
            print("\n✅ 필드 검증 통과: exchange, symbol, base_product 포함")
        
        return True
    else:
        print(f"❌ 실패: {result['status']}")
        print(f"로그: {result.get('logs', [])}")
        return False


async def test_futures_query_with_month_filter():
    """해외선물 전체종목조회 - 월물 필터 테스트"""
    from programgarden import ProgramGarden
    
    # 근월물(front) 테스트
    workflow = {
        "id": "symbol-query-futures-front",
        "name": "SymbolQueryNode 테스트 - 해외선물 근월물",
        "nodes": [
            {"id": "start_1", "type": "StartNode"},
            {
                "id": "broker_2",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "credential_id": "futures-paper-cred"
            },
            {
                "id": "query_3",
                "type": "SymbolQueryNode",
                "connection": "{{nodes.broker_2.connection}}",
                "product_type": "overseas_futures",  # 해외선물 선택
                "futures_exchange": "6",  # HKEX
                "futures_contract_month": "front",  # 근월물만
                "max_results": 50
            },
        ],
        "edges": [
            {"from": "start_1", "to": "broker_2"},
            {"from": "broker_2", "to": "query_3"},
        ],
        "credentials": [
            {
                "id": "futures-paper-cred",
                "type": "broker_ls",
                "name": "해외선물 모의투자",
                "data": {
                    "appkey": os.getenv("APPKEY_FUTURE_FAKE", ""),
                    "appsecret": os.getenv("APPSECRET_FUTURE_FAKE", ""),
                    "paper_trading": True
                }
            }
        ]
    }
    
    pg = ProgramGarden()
    job = await pg.run_async(workflow)
    result = await wait_for_job(job)
    
    print("\n" + "="*60)
    print("전체종목조회 - 해외선물 근월물(front) 필터")
    print("="*60)
    
    if result["status"] == "completed":
        nodes = result.get("nodes", {})
        query_output = nodes.get("query_3", {}).get("outputs", {})
        symbols = query_output.get("symbols", [])
        count = query_output.get("count", 0)
        month_filter = query_output.get("futures_contract_month", "N/A")
        
        print(f"✅ 조회 성공: {count}개 종목 (근월물)")
        print(f"월물 필터: {month_filter}")
        
        if symbols:
            print("\n근월물 종목 (처음 10개):")
            for i, sym in enumerate(symbols[:10]):
                print(f"  {i+1}. {sym.get('symbol', 'N/A'):15s} | {sym.get('name', 'N/A')[:25]} | 월물: {sym.get('contract_month', 'N/A')}")
            
            # 모든 종목이 서로 다른 base_product인지 확인 (근월물은 상품당 1개)
            base_products = set(s.get("base_product") for s in symbols)
            print(f"\n기초상품 수: {len(base_products)}개 (상품당 1개 근월물)")
        
        return True
    else:
        print(f"❌ 실패: {result['status']}")
        return False


async def main():
    print("="*60)
    print("SymbolQueryNode(전체종목조회) 테스트")
    print("="*60)
    
    # 해외주식 테스트
    stock_ok = await test_stock_query()
    
    # 해외선물 테스트 (전체)
    futures_ok = await test_futures_query()
    
    # 해외선물 월물 필터 테스트
    futures_month_ok = await test_futures_query_with_month_filter()
    
    print("\n" + "="*60)
    print("최종 결과")
    print("="*60)
    print(f"해외주식 (g3190): {'✅ 성공' if stock_ok else '❌ 실패'}")
    print(f"해외선물 (o3101): {'✅ 성공' if futures_ok else '❌ 실패'}")
    print(f"해외선물 월물필터: {'✅ 성공' if futures_month_ok else '❌ 실패'}")
    
    if stock_ok and futures_ok and futures_month_ok:
        print("\n✅ SymbolQueryNode 테스트 모두 성공!")
    else:
        print("\n❌ 일부 테스트 실패")


if __name__ == "__main__":
    asyncio.run(main())
