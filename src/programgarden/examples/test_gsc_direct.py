"""GSC 실시간 해외주식 시세 - 직접 테스트"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "finance"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from programgarden_finance import LS, GSC
import logging

# DEBUG 레벨로 상세 로그 확인
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# HTTP 관련 노이즈 줄이기
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.INFO)


async def test_gsc():
    ls = LS.get_instance()

    # 해외주식 실계좌 키 사용
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    logger.info(f"APPKEY: {appkey[:10]}...")
    
    login_result = ls.login(
        appkey=appkey,
        appsecretkey=appsecret,
        paper_trading=False  # 해외주식은 모의투자 미지원
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    logger.info("로그인 성공!")

    client = ls.overseas_stock().real()
    await client.connect()
    logger.info("WebSocket 연결 완료")

    gsc = client.GSC()
    
    # AAPL: 나스닥 종목 (거래소코드 82)
    # 형식: {거래소코드}{심볼}
    symbols = ["82AAPL", "82TSLA", "82NVDA"]
    logger.info(f"구독 심볼: {symbols}")
    
    tick_count = 0
    
    def on_message(resp: GSC.GSCRealResponse):
        nonlocal tick_count
        logger.info(f"=== GSC 수신 ===")
        logger.info(f"rsp_cd: {resp.rsp_cd}, rsp_msg: {resp.rsp_msg}")
        
        # body 속성 직접 접근
        body = resp.body
        if body is not None:
            tick_count += 1
            symbol = body.symbol if hasattr(body, 'symbol') else '?'
            price = body.price if hasattr(body, 'price') else 0
            totq = body.totq if hasattr(body, 'totq') else 0
            logger.info(f"[{tick_count}] symbol: {symbol}, price: {price}, totq: {totq}")
        else:
            logger.warning("body가 None입니다! (구독 확인)")
    
    gsc.add_gsc_symbols(symbols=symbols)
    gsc.on_gsc_message(on_message)

    logger.info("60초 동안 데이터 수신 대기...")
    await asyncio.sleep(60)
    
    logger.info(f"테스트 종료 - 수신된 틱: {tick_count}개")
    
    gsc.remove_gsc_symbols(symbols=symbols)
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_gsc())
