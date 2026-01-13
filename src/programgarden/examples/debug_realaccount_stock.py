"""
디버그: RealAccountNode 해외주식 문제 진단

positions=null, balance=null 반환 문제 확인
"""

import asyncio
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_stock_tracker_direct():
    """StockAccountTracker를 직접 호출하여 문제 진단"""
    
    # 1. credentials 로드 (환경변수 또는 파일에서)
    import json
    cred_path = os.path.expanduser("~/.programgarden/credentials.json")
    
    if not os.path.exists(cred_path):
        print(f"❌ credentials 파일 없음: {cred_path}")
        print("   환경변수 LS_APPKEY, LS_APPSECRET 설정 또는 파일 생성 필요")
        return
    
    with open(cred_path) as f:
        creds = json.load(f)
    
    # LS 증권 credential 찾기
    ls_cred = None
    for cred in creds:
        if cred.get("type") == "broker_ls":
            ls_cred = cred.get("data", {})
            break
    
    if not ls_cred or not ls_cred.get("appkey"):
        print("❌ broker_ls 타입의 credential이 없거나 appkey가 비어있음")
        return
    
    print(f"✅ Credentials 로드됨 (appkey: {ls_cred['appkey'][:8]}...)")
    
    # 2. LS 클라이언트 생성
    from programgarden_finance import LS
    
    ls = LS(
        appkey=ls_cred["appkey"],
        appsecret=ls_cred["appsecret"],
        paper_trading=ls_cred.get("paper_trading", "") == "true"
    )
    
    # 3. 토큰 발급
    print("\n📡 토큰 발급 중...")
    await ls.init()
    print("✅ 토큰 발급 완료")
    
    # 4. 해외주식 API 직접 호출 테스트
    print("\n" + "="*60)
    print("📋 해외주식 API 직접 호출 테스트 (COSOQ00201)")
    print("="*60)
    
    try:
        from programgarden_finance.ls.overseas_stock.accno.COSOQ00201.blocks import COSOQ00201InBlock1
        from datetime import datetime
        
        accno = ls.overseas_stock().accno()
        
        tr = accno.cosoq00201(
            body=COSOQ00201InBlock1(
                RecCnt=1,
                BaseDt=datetime.now().strftime("%Y%m%d"),
                CrcyCode="ALL",
                AstkBalTpCode="00"
            )
        )
        resp = await tr.req_async()
        
        print(f"\n응답 코드: {resp.rsp_cd}")
        print(f"응답 메시지: {getattr(resp, 'rsp_msg', 'N/A')}")
        
        # OutBlock1 확인 (기본 정보)
        if hasattr(resp, 'block1') and resp.block1:
            for item in resp.block1:
                print(f"\n📊 OutBlock1: 총 건수={getattr(item, 'RecCnt', 0)}")
        
        # OutBlock3 확인 (통화별 잔고)
        if hasattr(resp, 'block3') and resp.block3:
            print("\n💰 OutBlock3 (통화별 잔고):")
            for item in resp.block3:
                print(f"  - {item.CrcyCode}: 예수금={item.FcurrDps}, 평가금액={item.FcurrEvalAmt}")
        else:
            print("\n⚠️ OutBlock3 (통화별 잔고) 없음")
        
        # OutBlock4 확인 (종목별 잔고)
        if hasattr(resp, 'block4') and resp.block4:
            print(f"\n📈 OutBlock4 (종목별 잔고): {len(resp.block4)}개")
            for item in resp.block4:
                print(f"  - {item.ShtnIsuNo}: 수량={item.AstkBalQty}, 평단가={item.FcstckUprc}, 현재가={item.OvrsScrtsCurpri}")
        else:
            print("\n⚠️ OutBlock4 (종목별 잔고) 없음 - 보유종목이 없거나 조회 실패")
            
    except Exception as e:
        print(f"\n❌ API 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. StockAccountTracker 테스트
    print("\n" + "="*60)
    print("📋 StockAccountTracker 테스트")
    print("="*60)
    
    try:
        from decimal import Decimal
        
        # 실시간 클라이언트
        real_client = ls.overseas_stock().real()
        print(f"\n실시간 클라이언트 연결 중...")
        await real_client.connect()
        print(f"✅ WebSocket 연결됨")
        
        # Tracker 생성
        tracker = accno.account_tracker(
            real_client=real_client,
            refresh_interval=60,
            commission_rates={"DEFAULT": Decimal("0.0025")},
            tax_rates={"DEFAULT": Decimal("0")},
        )
        
        print(f"\n⏳ Tracker 시작...")
        await tracker.start()
        print(f"✅ Tracker 시작됨")
        
        # 데이터 확인
        positions = tracker.get_positions()
        balances = tracker.get_balances()
        
        print(f"\n📊 Tracker 결과:")
        print(f"  - positions: {positions}")
        print(f"  - positions 개수: {len(positions)}")
        print(f"  - balances: {balances}")
        print(f"  - balances keys: {list(balances.keys()) if isinstance(balances, dict) else type(balances)}")
        
        if positions:
            print(f"\n📈 보유종목 상세:")
            for sym, pos in positions.items():
                print(f"  - {sym}: qty={pos.quantity}, buy_price={pos.buy_price}, current={pos.current_price}")
        else:
            print(f"\n⚠️ 보유종목 없음")
        
        if balances:
            print(f"\n💰 잔고 상세:")
            for currency, bal in balances.items():
                print(f"  - {currency}: deposit={bal.deposit}, eval={bal.eval_amount}")
        else:
            print(f"\n⚠️ 잔고 없음")
        
        # 정리
        await tracker.stop()
        print(f"\n✅ Tracker 정지됨")
        
    except Exception as e:
        print(f"\n❌ Tracker 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stock_tracker_direct())
