"""
GOSS 종목 1개 매도 테스트
- NewOrderNode 바인딩 필드 수정 테스트용
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드
load_dotenv("/Users/jyj/ls_projects/programgarden/.env")

print("🔧 환경 변수 로드 완료")
print(f"   APPKEY: {os.getenv('APPKEY', 'NOT SET')[:10]}...")

async def main():
    print("📦 ProgramGarden 임포트 중...")
    from programgarden import ProgramGarden
    print("✅ 임포트 완료")
    
    workflow = {
        "id": "test-sell-goss",
        "name": "GOSS 1주 매도 테스트",
        "description": "NewOrderNode 테스트용",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "paper_trading": False,  # 실제 거래
                "appkey": os.getenv("APPKEY"),
                "appsecret": os.getenv("APPSECRET"),
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "GOSS"}
                ],
            },
            {
                "id": "market",
                "type": "MarketDataNode",
                "symbols": "{{ nodes.watchlist.symbols }}",
            },
            {
                "id": "order",
                "type": "NewOrderNode",
                "plugin": "MarketOrder",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "price_data": "{{ nodes.market.price }}",
                "fields": {
                    "side": "sell",
                    "amount_type": "fixed",
                    "amount": 1,
                },
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "market"},
            {"from": "market", "to": "order"},
        ],
    }
    
    print("=" * 60)
    print("🔄 GOSS 1주 매도 테스트 시작")
    print("=" * 60)
    
    pg = ProgramGarden()
    
    try:
        job = await pg.run_async(workflow)
        print(f"\n✅ Job 시작: {job.job_id}")
        print(f"   상태: {job.status}")
        
        # 잠시 대기 (비동기 실행 완료 대기)
        await asyncio.sleep(5)
        
        # 결과 확인
        if hasattr(job, 'context') and job.context:
            print(f"\n📦 노드별 출력:")
            for node_id in ["start", "broker", "watchlist", "market", "order"]:
                try:
                    output = job.context.get_all_outputs(node_id)
                    print(f"   {node_id}: {output}")
                except Exception as e:
                    print(f"   {node_id}: (에러: {e})")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
