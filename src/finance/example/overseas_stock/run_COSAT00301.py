"""
해외주식 신규 주문 (COSAT00301) 예시

GOSS(Gossamer Bio) 동전주 매수 테스트용
- NASDAQ(82) 지정가 주문
- Account Tracker 테스트와 함께 사용

사용법:
1. 먼저 run_account_tracker.py 실행 (터미널 1)
2. 이 파일 실행하여 주문 (터미널 2)
3. Tracker 터미널에서 AS0 이벤트 및 콜백 확인
"""

import logging
from dotenv import load_dotenv
import os
import asyncio
from programgarden_finance import LS, COSAT00301
from programgarden_finance.ls.models import SetupOptions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

load_dotenv()


async def buy_goss():
    """GOSS 1주 지정가 매수 주문"""
    
    ls = LS()  # 새 인스턴스 (싱글톤 아님)
    
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )
    
    if login_result is False:
        logger.error("로그인 실패")
        return
    
    # ===== 주문 파라미터 설정 =====
    # GOSS 현재가: $3.32 (2024-12-30 조회)
    ORDER_PRICE = 3.32  # 현재가로 지정가 주문 (체결 유도)
    ORDER_QTY = 1       # 1주
    
    print("=" * 50)
    print("📝 GOSS 매수 주문 정보")
    print("=" * 50)
    print(f"  종목: GOSS (Gossamer Bio)")
    print(f"  시장: NASDAQ (82)")
    print(f"  구분: 매수")
    print(f"  수량: {ORDER_QTY}주")
    print(f"  가격: ${ORDER_PRICE} (지정가)")
    print("=" * 50)
    
    # 자동 확인 모드 (환경 변수로 제어)
    if os.getenv("AUTO_CONFIRM") != "1":
        confirm = input("\n주문을 진행하시겠습니까? (y/n): ")
        if confirm.lower() != 'y':
            print("주문 취소됨")
            return
    else:
        print("\n[AUTO_CONFIRM=1] 자동 주문 진행...")
    
    # 주문 실행
    cosat00301 = ls.overseas_stock().주문().cosat00301(
        COSAT00301.COSAT00301InBlock1(
            RecCnt=1,
            OrdPtnCode="02",        # 02: 매수
            OrdMktCode="82",        # 82: NASDAQ
            IsuNo="GOSS",           # 종목코드
            OrdQty=ORDER_QTY,       # 주문수량
            OvrsOrdPrc=ORDER_PRICE, # 주문가격
            OrdprcPtnCode="00",     # 00: 지정가
        ),
        options=SetupOptions(
            on_rate_limit="wait"
        )
    )
    
    print("\n🚀 주문 전송 중...")
    result = await cosat00301.req_async()
    
    if result:
        print(f"\n응답 코드: {result.rsp_cd}")
        print(f"응답 메시지: {result.rsp_msg}")
        
        if result.block2:
            print("\n✅ 주문 접수 완료!")
            print(f"  주문번호: {result.block2.OrdNo}")
            print(f"  계좌명: {result.block2.AcntNm}")
            print(f"  종목명: {result.block2.IsuNm}")
        elif result.block1:
            print(f"\n⚠️  Block1 응답:")
            print(f"  종목: {result.block1.IsuNo}")
            print(f"  주문수량: {result.block1.OrdQty}")
            print(f"  주문가격: ${result.block1.OvrsOrdPrc}")
        
        if result.error_msg:
            print(f"\n❌ 오류: {result.error_msg}")
    else:
        print(f"\n❌ 주문 실패: 응답 없음")


async def sell_goss():
    """GOSS 1주 지정가 매도 주문 (청산용)"""
    
    ls = LS()  # 새 인스턴스 (싱글톤 아님)
    
    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )
    
    if login_result is False:
        logger.error("로그인 실패")
        return
    
    # ===== 주문 파라미터 설정 =====
    ORDER_PRICE = 3.32  # GOSS 현재가
    ORDER_QTY = 1       # 1주
    
    print("=" * 50)
    print("📝 GOSS 매도 주문 정보")
    print("=" * 50)
    print(f"  종목: GOSS (Gossamer Bio)")
    print(f"  시장: NASDAQ (82)")
    print(f"  구분: 매도")
    print(f"  수량: {ORDER_QTY}주")
    print(f"  가격: ${ORDER_PRICE} (지정가)")
    print("=" * 50)
    
    if os.getenv("AUTO_CONFIRM") != "1":
        confirm = input("\n주문을 진행하시겠습니까? (y/n): ")
        if confirm.lower() != 'y':
            print("주문 취소됨")
            return
    else:
        print("\n[AUTO_CONFIRM=1] 자동 주문 진행...")
    
    cosat00301 = ls.overseas_stock().주문().cosat00301(
        COSAT00301.COSAT00301InBlock1(
            RecCnt=1,
            OrdPtnCode="01",        # 01: 매도
            OrdMktCode="82",        # 82: NASDAQ
            IsuNo="GOSS",           # 종목코드
            OrdQty=ORDER_QTY,       # 주문수량
            OvrsOrdPrc=ORDER_PRICE, # 주문가격
            OrdprcPtnCode="00",     # 00: 지정가
        ),
        options=SetupOptions(
            on_rate_limit="wait"
        )
    )
    
    print("\n🚀 주문 전송 중...")
    result = await cosat00301.req_async()
    
    if result:
        print(f"\n응답 코드: {result.rsp_cd}")
        print(f"응답 메시지: {result.rsp_msg}")
        
        if result.block2:
            print("\n✅ 주문 접수 완료!")
            print(f"  주문번호: {result.block2.OrdNo}")
        
        if result.error_msg:
            print(f"\n❌ 오류: {result.error_msg}")
    else:
        print(f"\n❌ 주문 실패: 응답 없음")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sell":
        # python run_COSAT00301.py sell
        asyncio.run(sell_goss())
    else:
        # python run_COSAT00301.py (기본: 매수)
        asyncio.run(buy_goss())
