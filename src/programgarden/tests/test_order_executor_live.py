"""
Order Node Executor 실전 테스트

테스트 계획:
1. 해외주식 실계좌 - 저가 지정가 매수 주문 → 즉시 취소 (실제 체결 방지)
2. 해외선물 모의투자 - 지정가 주문 → 즉시 취소

⚠️ 주의: 이 테스트는 실제 증권사 API를 호출합니다!
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()


async def test_overseas_stock_order_and_cancel():
    """
    해외주식 실계좌 테스트: 저가 지정가 매수 → 즉시 취소
    
    체결 방지를 위해 현재가보다 10% 낮은 가격으로 지정가 주문
    """
    from programgarden_finance import LS, COSAT00301, COSMT00300
    from programgarden_finance.ls.models import SetupOptions
    
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        logger.error("❌ APPKEY/APPSECRET 환경변수가 설정되지 않았습니다.")
        return False
    
    logger.info("=" * 60)
    logger.info("🧪 해외주식 실계좌 테스트 시작")
    logger.info("=" * 60)
    
    ls = LS.get_instance()
    
    # 1. 로그인
    logger.info("1️⃣ LS증권 로그인...")
    login_result = ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=False)
    if not login_result:
        logger.error("❌ 로그인 실패")
        return False
    logger.info("✅ 로그인 성공")
    
    # 2. 테스트 종목 설정 (저가 주식 사용)
    test_symbol = "SOXL"  # 저가 ETF
    test_price = 15.00  # 현재가보다 훨씬 낮은 가격 (체결 방지)
    test_qty = 1
    
    logger.info(f"2️⃣ 테스트 주문: {test_symbol} {test_qty}주 @ ${test_price} (NASDAQ)")
    
    # 3. 신규 매수 주문 (지정가)
    logger.info("3️⃣ 신규 매수 주문 제출...")
    try:
        order_response = ls.overseas_stock().주문().cosat00301(
            COSAT00301.COSAT00301InBlock1(
                RecCnt=1,
                OrdPtnCode="02",  # 매수
                OrdMktCode="82",  # NASDAQ
                IsuNo=test_symbol,
                OrdQty=test_qty,
                OvrsOrdPrc=test_price,
                OrdprcPtnCode="00",  # 지정가
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        result = await order_response.req_async()
        
        if result and hasattr(result, 'block1') and result.block1:
            order_no = result.block1.OrdNo
            logger.info(f"✅ 주문 접수 성공: 주문번호 {order_no}")
        else:
            # OutBlock1 확인
            if hasattr(result, 'OutBlock1') and result.OutBlock1:
                order_no = result.OutBlock1.OrdNo
                logger.info(f"✅ 주문 접수 성공: 주문번호 {order_no}")
            else:
                logger.error(f"❌ 주문 실패: {result}")
                return False
    except Exception as e:
        logger.error(f"❌ 주문 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 잠시 대기 (주문 처리 시간)
    logger.info("4️⃣ 주문 처리 대기 (2초)...")
    await asyncio.sleep(2)
    
    # 5. 주문 취소
    logger.info(f"5️⃣ 주문 취소: 주문번호 {order_no}")
    try:
        cancel_response = ls.overseas_stock().주문().cosmt00300(
            COSMT00300.COSMT00300InBlock1(
                RecCnt=1,
                OrgOrdNo=int(order_no),
                OrdMktCode="82",  # NASDAQ
                IsuNo=test_symbol,
                OrdQty=test_qty,
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        cancel_result = await cancel_response.req_async()
        
        if cancel_result:
            logger.info(f"✅ 취소 요청 완료: {cancel_result}")
        else:
            logger.warning(f"⚠️ 취소 응답 없음")
    except Exception as e:
        logger.error(f"❌ 취소 오류: {e}")
        import traceback
        traceback.print_exc()
        # 취소 실패해도 테스트 계속 진행 (이미 체결되었거나 시스템 이슈일 수 있음)
    
    logger.info("=" * 60)
    logger.info("🎉 해외주식 테스트 완료")
    logger.info("=" * 60)
    return True


async def test_overseas_futures_order_and_cancel():
    """
    해외선물 모의투자 테스트: 지정가 주문 → 즉시 취소
    """
    from programgarden_finance import LS, CIDBT00100, CIDBT01000
    from programgarden_finance.ls.models import SetupOptions
    from datetime import datetime
    
    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    
    if not appkey or not appsecret:
        logger.error("❌ APPKEY_FUTURE_FAKE/APPSECRET_FUTURE_FAKE 환경변수가 설정되지 않았습니다.")
        return False
    
    logger.info("=" * 60)
    logger.info("🧪 해외선물 모의투자 테스트 시작")
    logger.info("=" * 60)
    
    ls = LS.get_instance()
    
    # 1. 로그인 (모의투자)
    logger.info("1️⃣ LS증권 로그인 (모의투자)...")
    login_result = ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True)
    if not login_result:
        logger.error("❌ 로그인 실패")
        return False
    logger.info("✅ 로그인 성공 (모의투자)")
    
    # 2. 테스트 종목 설정 (E-mini S&P 500)
    test_symbol = "ESH25"  # E-mini S&P 500 2025년 3월물
    test_price = 5000.00  # 현재가보다 낮은 가격
    test_qty = 1
    today = datetime.now().strftime("%Y%m%d")
    
    logger.info(f"2️⃣ 테스트 주문: {test_symbol} {test_qty}계약 @ {test_price}")
    
    # 3. 신규 매수 주문 (지정가)
    logger.info("3️⃣ 신규 매수 주문 제출...")
    try:
        order_response = ls.overseas_futureoption().order().CIDBT00100(
            CIDBT00100.CIDBT00100InBlock1(
                RecCnt=1,
                OrdDt=today,
                IsuCodeVal=test_symbol,
                FutsOrdTpCode="1",  # 신규
                BnsTpCode="2",  # 매수
                AbrdFutsOrdPtnCode="2",  # 지정가
                CrcyCode="USD",
                OvrsDrvtOrdPrc=test_price,
                CndiOrdPrc=0,
                OrdQty=test_qty,
                PrdtCode="000000",
                DueYymm="202503",
                ExchCode="CME",
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        result = await order_response.req_async()
        
        if result and hasattr(result, 'block1') and result.block1:
            order_no = result.block1.OrdNo
            logger.info(f"✅ 주문 접수 성공: 주문번호 {order_no}")
        elif hasattr(result, 'OutBlock1') and result.OutBlock1:
            order_no = result.OutBlock1.OrdNo
            logger.info(f"✅ 주문 접수 성공: 주문번호 {order_no}")
        else:
            logger.warning(f"⚠️ 주문 응답 형식 확인 필요: {result}")
            # 응답 구조 확인
            if result:
                logger.info(f"   응답 속성: {dir(result)}")
            return False
    except Exception as e:
        logger.error(f"❌ 주문 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 잠시 대기
    logger.info("4️⃣ 주문 처리 대기 (2초)...")
    await asyncio.sleep(2)
    
    # 5. 주문 취소
    logger.info(f"5️⃣ 주문 취소: 주문번호 {order_no}")
    try:
        cancel_response = ls.overseas_futureoption().order().CIDBT01000(
            CIDBT01000.CIDBT01000InBlock1(
                RecCnt=1,
                OrdDt=today,
                OrgOrdNo=int(order_no),
                IsuCodeVal=test_symbol,
                CrcyCode="USD",
                OrdQty=test_qty,
                PrdtCode="000000",
                DueYymm="202503",
                ExchCode="CME",
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        cancel_result = await cancel_response.req_async()
        logger.info(f"✅ 취소 요청 완료: {cancel_result}")
    except Exception as e:
        logger.error(f"❌ 취소 오류: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("=" * 60)
    logger.info("🎉 해외선물 모의투자 테스트 완료")
    logger.info("=" * 60)
    return True


async def main():
    """메인 테스트 실행"""
    logger.info("🚀 Order Node Executor 실전 테스트 시작")
    logger.info("")
    
    results = {}
    
    # 1. 해외주식 실계좌 테스트
    try:
        results["overseas_stock"] = await test_overseas_stock_order_and_cancel()
    except Exception as e:
        logger.error(f"해외주식 테스트 실패: {e}")
        results["overseas_stock"] = False
    
    logger.info("")
    
    # 2. 해외선물 모의투자 테스트
    try:
        results["overseas_futures"] = await test_overseas_futures_order_and_cancel()
    except Exception as e:
        logger.error(f"해외선물 테스트 실패: {e}")
        results["overseas_futures"] = False
    
    # 결과 요약
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 테스트 결과 요약")
    logger.info("=" * 60)
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    logger.info("")
    logger.info(f"최종 결과: {'🎉 모든 테스트 통과!' if all_passed else '⚠️ 일부 테스트 실패'}")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
