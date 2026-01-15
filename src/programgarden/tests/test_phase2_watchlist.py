"""
Phase 2: WatchlistNode 테스트
해외선물 관심종목 리스트 정의 및 symbols 출력 확인
"""
import asyncio
import json
import sys
import os

# 패키지 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from programgarden.client import ProgramGarden


WORKFLOW = {
    "id": "watchlist-futures-test",
    "name": "WatchlistNode 테스트 - 해외선물",
    "description": "WatchlistNode로 해외선물 관심종목 리스트 정의 및 출력 확인",
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
            "description": "해외선물 브로커 연결 (모의투자)",
            "provider": "ls-sec.co.kr",
            "product": "overseas_futures",
            "credential_id": "futures-paper-cred"
        },
        {
            "id": "watchlist_3",
            "type": "WatchlistNode",
            "category": "market",
            "position": {"x": 700, "y": 200},
            "description": "해외선물 관심종목 리스트",
            "connection": "{{nodes.broker_2.connection}}",
            "symbols": [
                {"exchange": "HKEX", "symbol": "HSIG26"},
                {"exchange": "HKEX", "symbol": "HCEIG26"},
                {"exchange": "CME", "symbol": "ESH26"},
                {"exchange": "CME", "symbol": "NQH26"}
            ]
        },
        {
            "id": "display_4",
            "type": "DisplayNode",
            "category": "analysis",
            "position": {"x": 1050, "y": 200},
            "description": "관심종목 리스트 표시",
            "size": {"width": 400, "height": 250}
        }
    ],
    "edges": [
        {"from": "start_1", "to": "broker_2"},
        {"from": "broker_2", "to": "watchlist_3"},
        {"from": "watchlist_3", "to": "display_4"}
    ],
    "credentials": [
        {
            "id": "futures-paper-cred",
            "type": "broker_ls",
            "name": "해외선물 모의투자",
            "data": {
                "appkey": os.getenv("APPKEY_FUTURE_FAKE", "PSntdlDvZjen1lf0tu9mfttUd3CTiMI8OZXv"),
                "appsecret": os.getenv("APPSECRET_FUTURE_FAKE", "pXxEQ02eYZyGZmNRGFWHfSlxZ5raHWCL"),
                "paper_trading": True
            }
        }
    ]
}


async def main():
    print("=" * 60)
    print("Phase 2: WatchlistNode 테스트")
    print("=" * 60)
    
    pg = ProgramGarden()
    
    print("\n[1] 워크플로우 실행 중...")
    job = await pg.run_async(WORKFLOW)
    
    # Job 완료 대기
    import asyncio
    for _ in range(50):  # 최대 5초 대기
        if hasattr(job, 'status') and job.status in ("completed", "failed", "stopped"):
            break
        await asyncio.sleep(0.1)
    
    result = job.get_state() if hasattr(job, 'get_state') else {}
    
    # nodes 딕셔너리에서 각 노드 출력 확인
    nodes_output = result.get("nodes", {})
    
    print("\n[2] 실행 결과:")
    print("-" * 40)
    print(f"Job Status: {result.get('status', 'unknown')}")
    
    # 각 노드별 출력 확인
    nodes_output = result.get("nodes", {})
    for node_id, output in nodes_output.items():
        print(f"\n📦 {node_id}:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    # WatchlistNode 출력 검증
    print("\n" + "=" * 60)
    print("[3] 검증 결과")
    print("=" * 60)
    
    watchlist_output = nodes_output.get("watchlist_3", {})
    outputs = watchlist_output.get("outputs", {})
    symbols = outputs.get("symbols", [])
    
    if symbols:
        print(f"✅ symbols 배열 정상 출력: {len(symbols)}개 종목")
        
        # 필드 검증
        first_symbol = symbols[0]
        has_exchange = "exchange" in first_symbol
        has_symbol = "symbol" in first_symbol
        has_exchange_code = "exchange_code" in first_symbol
        
        print(f"   - exchange 필드: {'✅' if has_exchange else '❌'}")
        print(f"   - symbol 필드: {'✅' if has_symbol else '❌'}")
        print(f"   - exchange_code 필드: {'✅' if has_exchange_code else '❌'}")
        
        if has_exchange and has_symbol:
            print("\n✅ WatchlistNode 테스트 성공!")
        else:
            print("\n❌ 필드 누락 - 확인 필요")
    else:
        print("❌ symbols 출력 없음")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
