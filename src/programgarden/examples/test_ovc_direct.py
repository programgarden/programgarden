"""OVC 직접 테스트"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "finance"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from programgarden_finance import LS, OVC
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


async def test_ovc():
    ls = LS.get_instance()

    # 해외선물 모의투자 키 사용
    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    
    logger.info(f"APPKEY: {appkey[:10]}...")
    
    login_result = ls.login(
        appkey=appkey,
        appsecretkey=appsecret,
        paper_trading=True  # 모의투자
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    logger.info("로그인 성공!")

    def on_message(resp: OVC.OVCRealResponse):
        logger.info(f"=== OVC 수신 ===")
        logger.info(f"rsp_cd: {resp.rsp_cd}, rsp_msg: {resp.rsp_msg}")
        if resp.body:
            logger.info(f"symbol: {resp.body.symbol}")
            logger.info(f"curpr: {resp.body.curpr}")
            logger.info(f"totq: {resp.body.totq}")
        else:
            logger.warning("body가 None입니다!")

    client = ls.overseas_futureoption().real()
    await client.connect()
    logger.info("WebSocket 연결 완료")

    ovc = client.OVC()
    
    # 1월물 (F) 사용 - 근월물이라 거래가 더 활발할 수 있음
    symbols = ["HSIF26  ", "HCEIF26 ", "HTIF26  "]  # 8자리 패딩
    logger.info(f"구독 심볼: {symbols}")
    
    tick_count = 0
    
    def on_message_with_count(resp: OVC.OVCRealResponse):
        nonlocal tick_count
        logger.info(f"=== OVC 수신 ===")
        logger.info(f"rsp_cd: {resp.rsp_cd}, rsp_msg: {resp.rsp_msg}")
        if resp.body:
            tick_count += 1
            logger.info(f"[{tick_count}] symbol: {resp.body.symbol.strip()}, curpr: {resp.body.curpr}, totq: {resp.body.totq}")
        else:
            logger.warning("body가 None입니다! (구독 확인)")
    
    ovc.add_ovc_symbols(symbols=symbols)
    ovc.on_ovc_message(on_message_with_count)

    logger.info("60초 동안 데이터 수신 대기...")
    await asyncio.sleep(60)
    
    logger.info(f"테스트 종료 - 수신된 틱: {tick_count}개")

if __name__ == "__main__":
    asyncio.run(test_ovc())
