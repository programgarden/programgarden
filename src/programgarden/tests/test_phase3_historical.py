"""
Phase 3: HistoricalDataNode 테스트
해외주식 과거 일봉 데이터 조회 (g3103 API)
"""
import asyncio
import json
import sys
import os

# 패키지 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from programgarden.client import ProgramGarden


WORKFLOW = {
    "id": "historical-stock-test",
    "name": "HistoricalDataNode 테스트 - 해외주식",
    "description": "HistoricalDataNode로 해외주식 과거 일봉 데이터 조회 (g3103)",
    "nodes": [
        {
            "id": "start_1",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 50, "y": 200},
            "description": "워크플로우 시작"
        },
        {
            "id": "broker_2",
            "type": "BrokerNode",
            "category": "infra",
            "position": {"x": 350, "y": 200},
            "description": "해외주식 브로커 연결",
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "credential_id": "stock-real-cred"
        },
        {
            "id": "historical_3",
            "type": "HistoricalDataNode",
            "category": "market",
            "position": {"x": 700, "y": 200},
            "description": "AAPL, TSLA 과거 30일 일봉 조회",
            "connection": "{{nodes.broker_2.connection}}",
            "symbols": [
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NASDAQ", "symbol": "TSLA"}
            ],
            "interval": "1d",
            "start_date": "dynamic:days_ago(30)",
            "end_date": "dynamic:today()"
        },
        {
            "id": "display_4",
            "type": "DisplayNode",
            "category": "analysis",
            "position": {"x": 1050, "y": 200},
            "description": "OHLCV 데이터 표시 (테이블)",
            "size": {"width": 500, "height": 400}
        }
    ],
    "edges": [
        {"from": "start_1", "to": "broker_2"},
        {"from": "broker_2", "to": "historical_3"},
        {"from": "historical_3", "to": "display_4"}
    ],
    "credentials": [
        {
            "id": "stock-real-cred",
            "type": "broker_ls",
            "name": "해외주식 실계좌",
            "data": {
                "appkey": os.getenv("APPKEY", "PSCG5XnnxeVWVLNpj00lOLucXYs0fp866QYQ"),
                "appsecret": os.getenv("APPSECRET", "hywhsIEdVaLWl901H1ktmTyLvVBC7LVv"),
                "paper_trading": False
            }
        }
    ]
}


async def main():
    print("=" * 60)
    print("Phase 3: HistoricalDataNode 테스트")
    print("=" * 60)
    
    pg = ProgramGarden()
    
    print("\n[1] 워크플로우 실행 중...")
    job = await pg.run_async(WORKFLOW)
    
    # Job 완료 대기
    for _ in range(100):  # 최대 10초 대기
        if hasattr(job, 'status') and job.status in ("completed", "failed", "stopped"):
            break
        await asyncio.sleep(0.1)
    
    result = job.get_state() if hasattr(job, 'get_state') else {}
    nodes_output = result.get("nodes", {})
    
    print("\n[2] 실행 결과:")
    print("-" * 40)
    print(f"Job Status: {result.get('status', 'unknown')}")
    
    # HistoricalDataNode 출력만 확인
    historical_output = nodes_output.get("historical_3", {})
    outputs = historical_output.get("outputs", {})
    
    print(f"\n📦 historical_3:")
    print(f"   state: {historical_output.get('state', 'unknown')}")
    
    ohlcv_data = outputs.get("ohlcv_data", {})
    symbols = outputs.get("symbols", [])
    period = outputs.get("period", "")
    interval = outputs.get("interval", "")
    
    print(f"   period: {period}")
    print(f"   interval: {interval}")
    print(f"   symbols: {symbols}")
    
    # 각 종목별 데이터 수 확인
    for symbol, data in ohlcv_data.items():
        if isinstance(data, list):
            print(f"   {symbol}: {len(data)}개 데이터")
            if data:
                print(f"      첫 번째: {data[0]}")
                print(f"      마지막: {data[-1]}")
    
    # 검증
    print("\n" + "=" * 60)
    print("[3] 검증 결과")
    print("=" * 60)
    
    success = True
    
    # ohlcv_data 확인
    if ohlcv_data:
        print(f"✅ ohlcv_data 출력: {len(ohlcv_data)}개 종목")
        
        for symbol, data in ohlcv_data.items():
            if isinstance(data, list) and len(data) > 0:
                first_row = data[0]
                has_date = "date" in first_row
                has_open = "open" in first_row
                has_high = "high" in first_row
                has_low = "low" in first_row
                has_close = "close" in first_row
                has_volume = "volume" in first_row
                
                print(f"   {symbol}:")
                print(f"      - 데이터 수: {len(data)}개")
                print(f"      - date: {'✅' if has_date else '❌'}")
                print(f"      - open: {'✅' if has_open else '❌'}")
                print(f"      - high: {'✅' if has_high else '❌'}")
                print(f"      - low: {'✅' if has_low else '❌'}")
                print(f"      - close: {'✅' if has_close else '❌'}")
                print(f"      - volume: {'✅' if has_volume else '❌'}")
                
                if not all([has_date, has_open, has_high, has_low, has_close, has_volume]):
                    success = False
            else:
                print(f"   {symbol}: ❌ 데이터 없음")
                success = False
    else:
        print("❌ ohlcv_data 출력 없음")
        success = False
    
    if success:
        print("\n✅ HistoricalDataNode 테스트 성공!")
    else:
        print("\n❌ HistoricalDataNode 테스트 실패")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
