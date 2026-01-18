"""
OVC 실시간 테스트 - HKEX 종목
"""
import asyncio
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# 로깅 설정 (DEBUG 레벨)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 파일 경로
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)


async def test_ovc_hkex():
    """HKEX 종목 OVC 실시간 테스트"""
    from programgarden_finance import LS, OVC
    
    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    
    if not appkey or not appsecret:
        logger.error("APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE 환경변수가 필요합니다.")
        return
    
    logger.info("=" * 60)
    logger.info("OVC HKEX 종목 실시간 테스트 시작")
    logger.info("=" * 60)
    
    ls = LS()
    # paper_trading=True로 로그인해야 모의투자 WebSocket URL 사용
    if not ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True):
        logger.error("로그인 실패")
        return
    
    logger.info(f"✅ 로그인 성공 (paper_trading=True)")
    logger.info(f"   WSS URL: {ls.token_manager.wss_url}")
    
    # 실시간 클라이언트 연결
    real_client = ls.overseas_futureoption().real()
    await real_client.connect()
    logger.info("✅ WebSocket 연결 완료")
    
    # OVC 구독 설정
    ovc = real_client.OVC()
    
    # HKEX 종목 심볼 - 다양한 형식 테스트
    test_symbols = [
        "HSIG26  ",   # 8자리 패딩
        "HCEIG26 ",   # 7자리 + 1패딩
        "HTIG26  ",   # 6자리 + 2패딩
    ]
    
    logger.info(f"구독할 심볼: {test_symbols}")
    
    received_data = []
    
    def on_tick(resp):
        """OVC 틱 수신 콜백"""
        logger.info(f"🔔 OVC 틱 수신: {resp}")
        received_data.append(resp)
    
    ovc.on_ovc_message(on_tick)
    ovc.add_ovc_symbols(symbols=test_symbols)
    logger.info(f"✅ OVC 구독 요청 완료")
    
    # 30초 대기
    logger.info("⏳ 30초간 실시간 데이터 대기 중...")
    for i in range(30):
        await asyncio.sleep(1)
        if received_data:
            logger.info(f"  {i+1}초: {len(received_data)}개 데이터 수신")
        else:
            logger.info(f"  {i+1}초: 대기 중...")
    
    # 결과 출력
    logger.info("-" * 40)
    logger.info(f"총 수신 데이터: {len(received_data)}개")
    for data in received_data[:5]:  # 최대 5개만 출력
        logger.info(f"  {data}")
    
    # 연결 종료
    ovc.remove_ovc_symbols(symbols=test_symbols)
    await real_client.close()
    logger.info("✅ WebSocket 연결 종료")


if __name__ == "__main__":
    asyncio.run(test_ovc_hkex())
