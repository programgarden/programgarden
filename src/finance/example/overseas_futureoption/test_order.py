"""해외선물 현재가 및 주문 테스트"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from programgarden_finance import LS, o3105, CIDBT00100

load_dotenv()

async def main():
    ls = LS.get_instance()
    
    # 모의투자 로그인
    login = ls.login(
        appkey=os.getenv('APPKEY_FUTURE_FAKE'),
        appsecretkey=os.getenv('APPSECRET_FUTURE_FAKE'),
        paper_trading=True,
    )
    
    if not login:
        print("❌ 로그인 실패")
        return
    
    print("✅ 모의투자 로그인 성공")
    
    # 테스트 종목: Mini Hang Seng (증거금 낮음)
    symbol = "HMHF26"  # Mini Hang Seng 2026년 1월물
    
    # 1. 현재가 조회
    print(f"\n📊 {symbol} 현재가 조회")
    print("=" * 50)
    
    req = ls.overseas_futureoption().market().o3105(
        body=o3105.O3105InBlock(symbol=symbol)
    )
    result = await req.req_async()
    
    if result.block:
        b = result.block
        print(f"  종목: {b.SymbolNm}")
        print(f"  현재가: {b.CloseP}")
        print(f"  시가: {b.OpenP}")
        print(f"  고가: {b.HighP}")
        print(f"  저가: {b.LowP}")
        current_price = float(b.CloseP)
    else:
        print(f"  조회 실패: {result.rsp_msg}")
        # 임의 가격으로 진행
        current_price = 20000
    
    # 2. 매수 주문 (지정가 - 현재가보다 높게)
    order_price = current_price + 50  # 현재가보다 50포인트 높게 (즉시 체결 유도)
    
    print(f"\n📝 {symbol} 매수 주문 (지정가 {order_price})")
    print("=" * 50)
    
    ord_dt = datetime.now().strftime("%Y%m%d")
    
    order_req = ls.overseas_futureoption().order().CIDBT00100(
        body=CIDBT00100.CIDBT00100InBlock1(
            OrdDt=ord_dt,
            IsuCodeVal=symbol,
            FutsOrdTpCode="1",       # 1: 신규
            BnsTpCode="2",           # 2: 매수
            AbrdFutsOrdPtnCode="2",  # 2: 지정가
            OvrsDrvtOrdPrc=order_price,
            CndiOrdPrc=0,
            OrdQty=1,
        )
    )
    
    order_result = await order_req.req_async()
    
    print(f"응답: [{order_result.rsp_cd}] {order_result.rsp_msg}")
    
    if hasattr(order_result, 'block2') and order_result.block2:
        print(f"✅ 주문번호: {order_result.block2.OrdNo}")
    elif hasattr(order_result, 'block1') and order_result.block1:
        b1 = order_result.block1
        print(f"  주문일: {getattr(b1, 'OrdDt', '')}")
        print(f"  종목: {getattr(b1, 'IsuCodeVal', '')}")
    
    print("\n✅ 완료")

asyncio.run(main())
